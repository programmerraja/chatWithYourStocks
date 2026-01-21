import csv
from datetime import datetime, timezone
from pathlib import Path
from src.core.database import get_db


HOLDINGS_SCHEMA = {
    'AsOfDate': 'date',
    'OpenDate': 'date',
    'CloseDate': 'date',
    'ShortName': 'str',
    'PortfolioName': 'str',
    'StrategyRefShortName': 'str',
    'Strategy1RefShortName': 'str',
    'Strategy2RefShortName': 'str',
    'CustodianName': 'str',
    'DirectionName': 'str',
    'SecurityId': 'str',
    'SecurityTypeName': 'str',
    'SecName': 'str',
    'StartQty': 'float',
    'Qty': 'float',
    'StartPrice': 'float',
    'Price': 'float',
    'StartFXRate': 'float',
    'FXRate': 'float',
    'MV_Local': 'float',
    'MV_Base': 'float',
    'PL_DTD': 'float',
    'PL_QTD': 'float',
    'PL_MTD': 'float',
    'PL_YTD': 'float',
}

TRADES_SCHEMA = {
    'id': 'str',
    'RevisionId': 'str',
    'AllocationId': 'str',
    'TradeTypeName': 'str',
    'SecurityId': 'str',
    'SecurityType': 'str',
    'Name': 'str',
    'Ticker': 'str',
    'CUSIP': 'str',
    'ISIN': 'str',
    'TradeDate': 'date',
    'SettleDate': 'date',
    'Quantity': 'float',
    'Price': 'float',
    'TradeFXRate': 'float',
    'Principal': 'float',
    'Interest': 'float',
    'TotalCash': 'float',
    'AllocationQTY': 'float',
    'AllocationPrincipal': 'float',
    'AllocationInterest': 'float',
    'AllocationFees': 'float',
    'AllocationCash': 'float',
    'PortfolioName': 'str',
    'CustodianName': 'str',
    'StrategyName': 'str',
    'Strategy1Name': 'str',
    'Strategy2Name': 'str',
    'Counterparty': 'str',
    'AllocationRule': 'str',
    'IsCustomAllocation': 'bool',
}


def convert_value(value, value_type):
    if not value or value.strip() == '':
        return None
    
    value = value.strip()
    
    if value_type == 'date':
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None
    
    if value_type == 'float':
        try:
            return float(value)
        except ValueError:
            return None
    
    if value_type == 'int':
        try:
            return int(value)
        except ValueError:
            return None
    
    if value_type == 'bool':
        return value.lower() in ('true', '1', 'yes')
    
    return value


def load_csv(csv_path, schema):
    records = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = {}
            for field, value in row.items():
                field_type = schema.get(field, 'str')
                record[field] = convert_value(value, field_type)
            record['created_at'] = datetime.now(timezone.utc)
            record['updated_at'] = datetime.now(timezone.utc)
            records.append(record)
    return records


def insert_batch(collection, records, batch_size=1000):
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        result = collection.insert_many(batch)
        total += len(result.inserted_ids)
    return total


def load_holdings(csv_path):
    records = load_csv(csv_path, HOLDINGS_SCHEMA)
    db = get_db()
    return insert_batch(db.holdings, records)


def load_trades(csv_path):
    records = load_csv(csv_path, TRADES_SCHEMA)
    db = get_db()
    return insert_batch(db.trades, records)


def ingest_data(holdings_path=None, trades_path=None):
    db = get_db()
    db.connect()
    
    total_holdings = 0
    total_trades = 0
    
    if holdings_path and Path(holdings_path).exists():
        total_holdings = load_holdings(holdings_path)
    
    if trades_path and Path(trades_path).exists():
        total_trades = load_trades(trades_path)
    
    print(f"Holdings: {total_holdings} | Trades: {total_trades}")
    
    db.disconnect()


if __name__ == "__main__":
    
    holdings_csv = "./src/data/holdings.csv"
    trades_csv = "./src/data/trades.csv"
    
    ingest_data(holdings_csv, trades_csv)
