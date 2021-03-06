from bs4 import BeautifulSoup
from datetime import datetime
import time
import requests
from init_database_postgre import load_db_credential_info
from real_time_web_scraper import update_insider_trades, write_to_csv

insider_trades = []
trading_activity = {'B': 'Buy', 'S': 'Sell', 'O': 'Options Excersise'}


def parse_row_info(trades, trade_type):
    """
    :param trades:
    Contains usually 7 indexes, which are:
    Ticker, Company Information, Person Filling & Position, Buy/Sell or Options Excersize, Share and Price,
    Value, Trade Date & Time
    :return:
    """
    # Find the time now, in UTC time
    now = datetime.utcnow()

    # Check to see if it contains symbol and company info, otherwise use previous
    if len(trades[-1]) == 0:
        return
    # If it contains content, that means we have a new equity / company
    if len(trades[0]) > 1:
        symbol = trades[0]
        company = trades[1].split('  ')
        company = company[0]
    # Otherwise, we use the latest entry for company and symbol
    else:
        last_trade = insider_trades[-1]
        symbol = last_trade[0]
        company = last_trade[1]
    # If we detect a '(' in the name, then we can parse out the position of the insider
    if '(' in trades[2]:
        # insider, insider_position = trades[2].split("(")
        info = trades[2].split("(")

        if len(info) > 2:
            insider = info[0:-2]
            insider_position = info[-1]
            insider = insider[0].strip()
        else:
            insider, insider_position = trades[2].split("(")

    else:
        insider = trades[2]
        insider_position = ''
        insider = insider.strip()

    insider_position = insider_position[:-1]

    # Assign values to index 3 to 5 of the trades array
    trade_shares, trade_price, trade_value = trades[3:6]

    # Convert all values to float
    trade_value = float(trade_value.replace(",", ""))
    trade_shares = float(trade_shares.replace(",", ""))
    trade_price = float(trade_price.replace(",", ""))

    trade_date = datetime.strptime(trades[6], '%Y-%m-%d')

    insider_trades.append(
        [symbol, company, insider, insider_position, trade_type, trade_shares, trade_price, trade_value, trade_date,
         now])
    return


def find_pages_of_trades(soup_body):
    """
    This function is used to determine the number of pages given from the bs4 search, it will then store all URLs
    of the subsequent links of the report.

    :param soup_body: Text body from BS4 that contains linkp, it will contain hrefs to all other pages of this day
    :return: A list of href urls for later concatenation and length of pages
    """
    length = 0
    url_dict = []

    for row in soup_body:
        # Find all rows
        urls = row.find_all('a', href=True)
        for row in urls:
            next_page_url = row['href']

            # Check for redundancy
            if next_page_url in url_dict:
                pass
            else:
                # If not in the dictionary, then it is a unique link
                url_dict.append(next_page_url)
            length += 1
    return url_dict, length


def main():
    base_buy_url = 'https://www.insider-monitor.com/insiderbuy.php?days='
    base_report_url = 'https://www.insider-monitor.com/reports/'
    index = 1
    while index <= 10:
        # We navigate to the first day of insider buys
        url = base_buy_url + str(index)

        # Request to retrieve the first page
        response = requests.get(url)

        # Parse the text using bs4
        soup = BeautifulSoup(response.text, features='html.parser')

        # Retrieve the next page urls and length of pages in a particular day
        page_urls, total_pages = find_pages_of_trades(soup.find_all("p", {"class": "linkp"}))

        # Now we parse the current page of the report
        current_page = 1

        # Instantiate table body of the first page
        table_body = soup.find_all('tr')[1:]

        # While loop to traverse through number of pages
        while current_page <= total_pages:
            # Parse each row in table body
            for row in table_body:
                # Find all table entries
                trade = row.find_all('td')
                # Go through each row in table and strip the text
                row_info = [x.text.strip() for x in trade]
                # Parse the info from another python file
                parse_row_info(row_info, 'Buy')

            current_page += 1
            # Concatenate next url, if we do not see any additional URLS it means we are at the end of the pages
            if len(page_urls) == 0:
                break
            else:
                # Concactenate for our next url redirect
                next_page_url = base_report_url + page_urls[0]
                # Get rid of the next url in the list
                page_urls.pop(0)

                # Request for another page on the same day
                response = requests.get(next_page_url)

                soup = BeautifulSoup(response.text, features='html.parser')
                table_body = soup.find_all('tr')[1:]
        index += 1

    '''
    Now that we have processed the past 10 days worth of trade, we will insert it 
    into the dictionary
    '''
    # name of our database credential files (.txt)
    db_credential_info = "database_info.txt"

    # create a path version of our text file
    db_credential_info_p = '/' + db_credential_info

    # create our instance variables for host, username, password and database name
    db_host, db_user, db_password, db_name = load_db_credential_info(db_credential_info_p)

    # Call update insider trades to have it inserted into the dictionary
    update_insider_trades(db_host, db_user, db_password, db_name, insider_trades)

    # Write to CSV file for all the entries
    write_to_csv(insider_trades)


if __name__ == "__main__":
    main()
    # 'https://www.insider-monitor.com/insiderbuy.php?days=1'
