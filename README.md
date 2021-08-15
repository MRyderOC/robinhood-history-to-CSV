# robinhood-history-to-CSV

Extracting transaction history from Robinhood website and write them in CSV file.

## Technologies

**Python 3.8**
#### Required libraries
- bs4
- python-dotenv
- selenium

## How to use
1. Clone the repo: ``` git clone https://github.com/MRyderOC/robinhood-history-to-CSV.git ```.
2. Create a virtual environment: ```python3 -m venv env```.
3. Activate the virtual environment: ```source env/bin/activate```
4. Install dependencies: ```pip3 install -r requirements.txt```.
5. Store your USERNAME and PASSWORD in `.env` file.
6. Run the script: ```python3 history_to_CSV.py```.
7. Find the CSV results in repo folder. 
8. Enjoy!

## Blog
You can find the related blog in [Medium](https://milad-tabrizi.medium.com/extracting-transaction-history-into-csv-from-robinhood-using-python-scraping-73dcdfecb868).
