import csv
import datetime
import typing
from argparse import ArgumentParser
from datetime import datetime
from locale import atof, setlocale, LC_NUMERIC


class Transaction(object):
    def __init__(self, date, type_, symbol, amount, st_gain=0.0, lt_gain=0.0):
        self.date = date
        self.type = type_
        self.symbol = symbol
        self.amount = amount
        self.st_gain = st_gain
        self.lt_gain = lt_gain

    def key(item):
        return (item.date, item.type, item.symbol, item.amount, item.st_gain, item.lt_gain)


def num(num_str):
    num_str = num_str.replace("$", "")
    if num_str in ("", "-"):
        return 0.0
    elif "(" in num_str:
        return atof(num_str.replace("(", "").replace(")", ""))
    else:
        return atof(num_str)


def _calculate_trading_basis(transactions, debug=False):
    running_cash_total = 0.0
    running_sales_total = 0.0
    running_gain = 0.0

    transactions_sorted = sorted(transactions, key=Transaction.key)

    for t in transactions_sorted:
        before_cash = running_cash_total
        before_sales = running_sales_total
        if t.type == "sell":
            running_sales_total += t.amount
            running_gain += t.st_gain + t.lt_gain
        elif t.type == "buy":
            leftover = t.amount
            if leftover >= running_sales_total:
                leftover -= running_sales_total
                running_sales_total = 0.0
                running_cash_total -= leftover
            elif leftover < running_sales_total:
                running_sales_total -= leftover

        if debug:
            print(Transaction.key(t), before_cash, running_cash_total, before_sales, running_sales_total, running_gain)

    return running_gain / abs(running_cash_total), running_cash_total, running_gain


def _symbol_included(text, include_symbols):
    if include_symbols:
        found = False
        for symbol in include_symbols:
            if symbol.upper() in text.upper():
                return True
        if not found:
            return False
    return True


def parse_tdameritrade_realized_gains_file(f, include_symbols, debug=False):
    transactions = []

    reader = csv.reader(f)
    next(reader)  # header
    for row in reader:
        description = row[0]
        if not _symbol_included(description, include_symbols):
            if debug:
                print("Excluding ", description)
            continue

        if row[1] == "":
            break
        open_date = datetime.strptime(row[3].strip(), "%m/%d/%y")
        open_amount = atof(row[4])
        close_date = datetime.strptime(row[5].strip(), "%m/%d/%y")
        close_amount = atof(row[6])
        st_gain = num(row[7])
        lt_gain = num(row[8])

        transactions.append(Transaction(open_date, "buy", description, open_amount, st_gain, lt_gain))
        transactions.append(Transaction(close_date, "sell", description, close_amount, st_gain, lt_gain))
    return transactions


def parse_fidelity_realized_gains_file(f, include_symbols, debug=False):
    transactions = []

    reader = csv.reader(f)
    next(reader)  # header
    for row in reader:
        description = row[0][0:row[0].find("(")]
        if not _symbol_included(description, include_symbols):
            if debug:
                print("Excluding ", description)
            continue

        if row[1] == "":
            break
        open_date = datetime.strptime(row[3].strip(), "%m/%d/%Y")
        open_amount = num(row[6])
        close_date = datetime.strptime(row[4].strip(), "%m/%d/%Y")
        close_amount = num(row[5])
        st_gain = num(row[7])
        lt_gain = num(row[8])

        transactions.append(Transaction(open_date, "buy", row[0], open_amount, st_gain, lt_gain))
        transactions.append(Transaction(close_date, "sell", row[0], close_amount, st_gain, lt_gain))
    return transactions


def main(ib_filenames: typing.List[str] = [], td_filenames: typing.List[str] = [],
         fidelity_filenames: typing.List[str] = [], output_dir=None, include_symbols_filename=None,
         debug=False):
    transactions = []

    include_symbols = None
    if include_symbols_filename:
        include_symbols = set([])
        with open(include_symbols_filename) as f:
            for l in f:
                include_symbols.add(l.strip())

    for fn in td_filenames:
        with open(fn) as f:
            transactions.extend(
                parse_tdameritrade_realized_gains_file(f=f, include_symbols=include_symbols, debug=debug))

    for fn in fidelity_filenames:
        with open(fn) as f:
            transactions.extend(parse_fidelity_realized_gains_file(f=f, include_symbols=include_symbols, debug=debug))

    print(_calculate_trading_basis(transactions, debug=debug))


if __name__ == "__main__":
    setlocale(LC_NUMERIC, "en_US.UTF-8")
    parser = ArgumentParser()
    parser.add_argument("--debug", action="store_true", default=False)
    parser.add_argument("--output-dir", type=str, default=None, help="Script will save tab-separated files here")
    parser.add_argument("--ib-files", type=str, nargs="+", default=[])
    parser.add_argument("--td-files", type=str, nargs="+", default=[])
    parser.add_argument("--fidelity-files", type=str, nargs="+", default=[])
    parser.add_argument("--include-symbols", type=str)

    args = parser.parse_args()
    main(output_dir=args.output_dir,
         ib_filenames=args.ib_files,
         td_filenames=args.td_files,
         fidelity_filenames=args.fidelity_files,
         include_symbols_filename=args.include_symbols,
         debug=args.debug)
