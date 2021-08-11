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
    loginURL = 'https://robinhood.com/login'
    driver.get(loginURL)

    # Entering username and password
    WebDriverWait(driver, 10).until(lambda d: d.find_element_by_tag_name('body')) # Wait until fully loaded
    usernameXPATH = '/html/body/div[1]/div[1]/div[2]/div/div/div/div/div/form/div/div/div[1]/label/div[2]/input'
    username = driver.find_element_by_xpath(usernameXPATH)
    passwordXPATH = '/html/body/div[1]/div[1]/div[2]/div/div/div/div/div/form/div/div/div[2]/label/div[2]/input'
    password = driver.find_element_by_xpath(passwordXPATH)
    username.send_keys(client_username)
    password.send_keys(client_password)

    # Signing in
    signInXPATH = '/html/body/div[1]/div[1]/div[2]/div/div/div/div/div/form/footer/div/button'
    driver.find_element_by_xpath(signInXPATH).click()
    
    time.sleep(3)
    try:
        # 2FA
        WebDriverWait(driver, 10).until(lambda d: d.find_element_by_tag_name('body'))
        buttonXPATH = '/html/body/div[1]/div[1]/div[2]/div/div/div/div/div/div/div/div/button'
        driver.find_element_by_xpath(buttonXPATH).click()
        # Sending the code
        WebDriverWait(driver, 10).until(lambda d: d.find_element_by_tag_name('body'))
        verificationXPATH='/html/body/div[1]/div[1]/div[2]/div/div/div/div/div/div/form/input'
        driver.find_element_by_xpath(verificationXPATH).send_keys(input('Please enter the code: '))
        continueXPATH='/html/body/div[1]/div[1]/div[2]/div/div/div/div/div/div/form/footer/div[2]/button'
        driver.find_element_by_xpath(continueXPATH).click()
    except:
        # Sending the code if you already register 2FA
        WebDriverWait(driver, 10).until(lambda d: d.find_element_by_tag_name('body'))
        verificationXPATH = '/html/body/div[1]/div[1]/div[2]/div/div/div/div/div/form/div[2]/div/label/div/input'
        driver.find_element_by_xpath(verificationXPATH).send_keys(input('Please enter the code: '))
        continueXPATH='/html/body/div[1]/div[1]/div[2]/div/div/div/div/div/form/footer/div[2]/button'
        driver.find_element_by_xpath(continueXPATH).click()

    # Go to the history page (Account -> History) to scrape the data
    accountXPATH = '/html/body/div[1]/main/div[2]/div/div/div/nav/div/div[2]/div/div[2]/div/div/a'
    WebDriverWait(driver, 10).until(lambda d: d.find_element_by_xpath(accountXPATH))
    driver.find_element_by_xpath(accountXPATH).click()
    historyXPATH = '/html/body/div[1]/main/div[2]/div/div/div/nav/div/div[2]/div/div[2]/div[2]/div/div[1]/a[6]/div'
    WebDriverWait(driver, 10).until(lambda d: d.find_element_by_xpath(historyXPATH))
    driver.find_element_by_xpath(historyXPATH).click()

    # Now we have to scroll to the bottom of the page to gather all data
    time.sleep(4)
    old_height = 0
    # heights = [0,] # To store the page height
    while True:
        new_height = int(driver.execute_script('return document.body.scrollHeight'))
        if old_height == new_height:
            break
        old_height = new_height
        # heights.append(int(driver.execute_script('return document.body.scrollHeight')))
        # if heights[-1] == heights[-2]: # To quit the loop when we reached the bottom
        #     break
        driver.execute_script('window.scrollTo(0,document.body.scrollHeight);')
        time.sleep(2)

    # Write the page source on disk
    source = driver.page_source
    with open(path, 'w') as f:
        f.write(source)

    driver.quit()
    return source


def comma_deleter(l: list) -> list: 
    '''Remove all occurrences of "," in a list and make the list CSV ready'''
    return [s.replace(',', '') for s in l]


def to_extract(path: str):
    '''Using BeautifulSoup to extract desired information from path'''

    interest, transfer, stocks, crypto, dividend, corpActions = [], [], [], [], [], []
    
    # Loading the data
    with codecs.open(path, 'r', 'utf-8') as f:
        soup = bs(f.read(), 'lxml').find('div', class_='col-12')

    # Button tags Extraction
    trxsButtons = soup.find_all('header', class_='rh-expandable-item-header-98210179')
    buttons = [trx.text.replace('\n', '') for trx in trxsButtons]

    # Div tags Extraction
    trxsDivs = soup.find_all('div', class_='css-2ae82m')
    divs = [','.join(comma_deleter([item.text[:] for item in trx.find_all('span', class_="css-ktio0g")])) for trx in trxsDivs]

    # Creating a list of corresponding buttons and divs
    divs_and_buttons = [{'buttons':buttons[i], 'divs':divs[i], 'visited':False} for i in range(len(trxsButtons))]
    del divs, buttons, trxsDivs, trxsButtons


    # Extracting stocks, cryptos, and corpActions
    for i in range(len(divs_and_buttons)):
        tmp = divs_and_buttons[i]['divs'].split(',')
        if tmp[0].isupper():
            if tmp[2].startswith('Forward') or tmp[2].startswith('Reverse'):
                corpActions.append(tmp)
            else:
                stocks.append(tmp)
            divs_and_buttons[i]['visited'] = True
        elif tmp[0].startswith('Market'):
            crypto.append(tmp)
            divs_and_buttons[i]['visited'] = True

    # Extracting transfers, interests, 
    # and build a list of dividends dicts for further use
    dividendListOfDicts = []
    for i in range(len(divs_and_buttons)):
        if 'Dividend' in divs_and_buttons[i]['buttons']:
            dividendListOfDicts.append(divs_and_buttons[i])
            divs_and_buttons[i]['visited'] = True
        elif divs_and_buttons[i]['buttons'].startswith('Interest'):
            interest.append(divs_and_buttons[i]['divs'])
            divs_and_buttons[i]['visited'] = True
        elif divs_and_buttons[i]['buttons'].startswith('Deposit') or divs_and_buttons[i]['buttons'].startswith('Withdrawal'): ##### prone to bug
            transfer.append(divs_and_buttons[i]['divs'])
            divs_and_buttons[i]['visited'] = True

    # Extracting dividends
    for item in dividendListOfDicts:
        name_and_date = item['buttons'][13:(item['buttons'].find('+'))].strip()
        if not(name_and_date.endswith('2020') or name_and_date.endswith('2021')):
            name_and_date += ', 2020'
        name_and_date = name_and_date.replace(',', '')
        name_and_date = name_and_date.split()
        date = name_and_date[-3][-3:] + ' ' + name_and_date[-2] + ' ' + name_and_date[-1]
        try:
            name = name_and_date[-4] + ' ' + name_and_date[-3][:-3]
        except:
            name = name_and_date[-3][:-3]
        dividend.append(name+','+date+','+item['divs'])

    # Extarcting other transactions that didn't include in other categories
    others = [item for item in divs_and_buttons if item['visited'] == False]

    # Writing to a file
    with open('stocks.csv', 'x') as f:
        f.write('Symbol,Type,Time in Force,Submitted,Status,Entered Quantity,Filled,Filled Quantity,Total,Regulatory Fee\n')
        for item in stocks:
            f.write(','.join(item)+'\n')
    
    with open('crypto.csv', 'x') as f:
        f.write('Type,Submitted,Status,Entered Amount,Filled,Filled Quantity,Total Notional\n')
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

    with open('corpActions.csv', 'x') as f:
        f.write('Symbol,Date Received,Type,Split Amount,Previous Shares,New Shares\n')
        for item in corpActions:
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