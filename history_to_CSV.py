import time
import os
import codecs

from dotenv import load_dotenv
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait


def find_history_page_by_selenium(client_username: str, client_password: str, path: str):
    '''Using selenium to get the source page of history and write it on a disk'''
    driver = webdriver.Firefox(executable_path='./geckodriver')

    time.sleep(2)
    # Load the Page
    login_url = 'https://robinhood.com/login'
    driver.get(login_url)

    # Entering username and password
    WebDriverWait(driver, 10).until(lambda d: d.find_element_by_tag_name('body'))
    time.sleep(2)
    username_xpath = '/html/body/div[1]/div[1]/div[2]/div/div/div/div/div/form/div/div/div[1]/div/label/div[2]/input'
    username = driver.find_element_by_xpath(username_xpath)
    password_xpath = '/html/body/div[1]/div[1]/div[2]/div/div/div/div/div/form/div/div/div[2]/div/label/div[2]/input'
    password = driver.find_element_by_xpath(password_xpath)
    username.send_keys(client_username)
    password.send_keys(client_password)

    # Signing in
    sign_in_xpath = '/html/body/div[1]/div[1]/div[2]/div/div/div/div/div/form/footer/div[1]/button'
    driver.find_element_by_xpath(sign_in_xpath).click()

    time.sleep(3)
    try:
        # 2FA
        WebDriverWait(driver, 10).until(lambda d: d.find_element_by_tag_name('body'))
        button_xpath = '/html/body/div[1]/div[1]/div[2]/div/div/div/div/div/div/div/div/button'
        driver.find_element_by_xpath(button_xpath).click()
        # Sending the code
        WebDriverWait(driver, 10).until(lambda d: d.find_element_by_tag_name('body'))
        verification_xpath = '/html/body/div[6]/div[3]/div/section/div/form/div/div/input'
        time.sleep(1)
        driver.find_element_by_xpath(verification_xpath).send_keys(input('Please enter the code: '))
        continue_xpath = '/html/body/div[6]/div[3]/div/section/div/footer/div[1]/button'
        driver.find_element_by_xpath(continue_xpath).click()
    except Exception:
        # Sending the code if you already register 2FA
        WebDriverWait(driver, 10).until(lambda d: d.find_element_by_tag_name('body'))
        verification_xpath = '/html/body/div[6]/div[3]/div/div/section/div/form/div/div/input'
        driver.find_element_by_xpath(verification_xpath).send_keys(input('Please enter the code: '))
        continue_xpath = '/html/body/div[6]/div[3]/div/div/section/div/footer/div[1]/button'
        driver.find_element_by_xpath(continue_xpath).click()

    # Go to the history page (Account -> History) to scrape the data
    account_xpath = '/html/body/div[1]/main/div[2]/div/div/div/nav/div/div[2]/div/div[2]/div[1]/div/a'
    WebDriverWait(driver, 10).until(lambda d: d.find_element_by_xpath(account_xpath))
    driver.find_element_by_xpath(account_xpath).click()
    history_xpath = '/html/body/div[1]/main/div[2]/div/div/div/nav/div/div[2]/div/div[2]/div[2]/div/div[1]/a[8]'
    WebDriverWait(driver, 10).until(lambda d: d.find_element_by_xpath(history_xpath))
    driver.find_element_by_xpath(history_xpath).click()

    # Now we have to scroll to the bottom of the page to gather all data
    time.sleep(4)
    old_height = 0
    while True:
        driver.execute_script('window.scrollTo(0,document.body.scrollHeight);')
        new_height = int(driver.execute_script('return document.body.scrollHeight'))
        if old_height == new_height:
            break
        old_height = new_height
        time.sleep(2)

    # Write the page source on disk
    source = driver.page_source
    with open(path, 'w') as f:
        f.write(source)

    driver.quit()
    return source


def comma_deleter(input_list: list) -> list:
    '''Remove all occurrences of "," in a list and make the list CSV ready'''
    return [s.replace(',', '') for s in input_list]


def to_extract(path: str):
    '''Using BeautifulSoup to extract desired information from path'''
    interest, transfer, stocks, crypto, dividend, corp_actions = [], [], [], [], [], []
    # Loading the data
    with codecs.open(path, 'r', 'utf-8') as f:
        soup = bs(f.read(), 'lxml').find('div', class_='col-12')

    # Button tags Extraction
    trxs_buttons = soup.find_all('header', class_='rh-expandable-item-header-98210179')
    buttons = [trx.text.replace('\n', '') for trx in trxs_buttons]

    # Div tags Extraction
    trxs_divs = soup.find_all('div', class_='css-1nkp1h7-Accordion')
    divs = [
        ','.join(
            ','.join(comma_deleter([
                item.text[:]
                for item in trx.find_all('div', class_="css-6e9jx2")
            ])).split(',')[1::2]
        )
        for trx in trxs_divs
    ]

    # Creating a list of corresponding buttons and divs
    divs_and_buttons = [
        {'buttons': buttons[i], 'divs': divs[i], 'visited':False}
        for i in range(len(trxs_buttons))
    ]
    del divs, buttons, trxs_divs, trxs_buttons

    # Extracting stocks, cryptos, and corp_actions
    for i in range(len(divs_and_buttons)):
        tmp = divs_and_buttons[i]['divs'].split(',')
        if tmp[0].isupper():
            if tmp[2].startswith('Forward') or tmp[2].startswith('Reverse'):
                corp_actions.append(tmp)
            else:
                stocks.append(tmp)
            divs_and_buttons[i]['visited'] = True
        elif tmp[0].startswith('Market'):
            crypto.append(tmp)
            divs_and_buttons[i]['visited'] = True

    # Extracting transfers, interests,
    # and build a list of dividends dicts for further use
    dividend_list_of_dicts = []
    for i in range(len(divs_and_buttons)):
        if 'Dividend' in divs_and_buttons[i]['buttons']:
            dividend_list_of_dicts.append(divs_and_buttons[i])
            divs_and_buttons[i]['visited'] = True
        elif divs_and_buttons[i]['buttons'].startswith('Interest'):
            interest.append(divs_and_buttons[i]['divs'])
            divs_and_buttons[i]['visited'] = True
        elif divs_and_buttons[i]['buttons'].startswith('Deposit') or\
                divs_and_buttons[i]['buttons'].startswith('Withdrawal'):  # prone to bug
            transfer.append(divs_and_buttons[i]['divs'])
            divs_and_buttons[i]['visited'] = True

    # Extracting dividends
    for item in dividend_list_of_dicts:
        name_and_date = item['buttons'][13:(item['buttons'].find('+'))].strip()
        if not(name_and_date.endswith('2020') or name_and_date.endswith('2021')):
            name_and_date += ', 2021'
        name_and_date = name_and_date.replace(',', '')
        name_and_date = name_and_date.split()
        date = name_and_date[-3][-3:] + ' ' + name_and_date[-2] + ' ' + name_and_date[-1]
        try:
            name = name_and_date[-4] + ' ' + name_and_date[-3][:-3]
        except Exception:
            name = name_and_date[-3][:-3]
        dividend.append(name+','+date+','+item['divs'])

    # Extarcting other transactions that didn't include in other categories
    others = [item for item in divs_and_buttons if not item['visited']]

    # Writing to a file
    with open('stocks.csv', 'x') as f:
        f.write(
            'Symbol,Type,Time in Force,Submitted,'
            'Status,Entered Quantity,Filled,'
            'Filled Quantity,Total,Regulatory Fee\n'
        )
        for item in stocks:
            f.write(','.join(item)+'\n')

    with open('crypto.csv', 'x') as f:
        f.write(
            'Type,Submitted,Status,Entered Amount,'
            'Filled,Filled Quantity,Total Notional\n'
        )
        for item in crypto:
            f.write(','.join(item)+'\n')

    with open('interest.csv', 'x') as f:
        f.write('Amount,Pay Period Start,Pay Period End\n')
        for item in interest:
            f.write(item+'\n')

    with open('transfer.csv', 'x') as f:
        f.write('Amount,Bank Account,Initiated,Status\n')
        for item in transfer:
            f.write(item+'\n')

    with open('dividend.csv', 'x') as f:
        f.write('Name,Date,Number of Shares,Amount per Share,Total Amount\n')
        for item in dividend:
            f.write(item+'\n')

    with open('corp_actions.csv', 'x') as f:
        f.write(
            'Symbol,Date Received,Type,Split Amount,'
            'Previous Shares,New Shares\n'
        )
        for item in corp_actions:
            f.write(','.join(item)+'\n')

    with open('others.csv', 'x') as f:
        for item in others:
            f.write(item['buttons']+item['divs']+'\n')


if __name__ == '__main__':
    path = 'history.html'
    load_dotenv()
    USERNAME = os.getenv('USERNAME')
    PASSWORD = os.getenv('PASSWORD')
    source = find_history_page_by_selenium(USERNAME, PASSWORD, path)
    time.sleep(3)
    to_extract(path)
