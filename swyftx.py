#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import argparse
import requests
import sys

FEE = 0.006

def get_key():
    ''' The script requires your API key to be stored in a local file named api_key.dat '''
    f = open("api_key.dat")
    line = f.readline()
    f.close()
    return line.rstrip()

def get_status():
    ''' Checks the connection with the INFO endpoint of the server.
        Result and API version is printed to console. '''
    
    r = requests.get(URL+'info/')
    if r:
        r = r.json()
        v = r['version']
        s = r['state']
        m = r['maintenanceMode']
        
        if s == 1 and not m:
            print(f'Successfully connected to server, version {v}.')
            result = True
        elif s == 2:
            print(f'Error in connecting to server.')
            result = False
        elif m:
            print(f'Server in maintenance mode.')
            result = False
    else:
        print(f'Could not establish connection to info endpoint.')
        result = False

    return result


class Swyftx():
    def __init__(self):
        self.status = False
        self.r = requests.get(URL)
        if self.r:
            self.token = self.refresh_token()
            if self.token:
                self.status        = True
                self.headers       = self.r.headers
                self.assets_listed = self.get_assets_listed()
                self.assets_traded = self.get_assets_traded()
                self.balances      = self.get_balances()
                self.transactions  = self.get_transactions()
                self.set_ratio_aud_usd()

    def set_ratio_aud_usd(self):
        ''' Sets the ratio between AUD and USD based on value in USDT '''
        for i in self.assets_traded:
            if i['code'] == 'USDT':
                self.ratio_aud_usd = self.get_ratio('AUD', 'USDT')

    def exists_currency(self, code):
        ''' Checks that currency exists in list of traded assets. AUD also returns True to support CLI validation. '''
        if code == 'AUD':
            return True
        for i in self.assets_traded:
            if i['code'] == code:
                return True
        return False
        
    def get_ratio(self, c1, c2):
        ''' Returns the ratio between two provided currencies '''
        if c1 == 'AUD':
            x = 1
        if c2 == 'AUD':
            y = 1
        for i in self.assets_traded:
            if i['code'] == c1:
                x = (float(i['buy']) + float(i['sell'])) / 2
            if i['code'] == c2:
                y = (float(i['buy']) + float(i['sell'])) / 2
        try:
            return y/x
        except:
            return None
        
    def do_request_get(self, addr, authToken=None): 
        ''' Helper function to perform GET operations on API either with or without authToken. '''
        if authToken == None:
            r = requests.get(addr)
        else:
            r = requests.get(addr, headers={'Authorization': 'Bearer ' + authToken})
        result = r.json()
        
        try:
            if 'error' in result.keys():
                result = []
        except:
            pass
            
        return result  
    
    def refresh_token(self):
        ''' Refreshes access token based on API key. '''
        r = requests.post(URL+'auth/refresh/', data={'apiKey': get_key()})
        r = r.json()
        if 'accessToken' in r.keys():
            result = r['accessToken']
        else:
            result = None
        return result

    def logout(self):
        ''' Logs out of the server and invalides the current access token. '''
        r = requests.post(URL+'auth/logout/', headers={'Authorization': 'Bearer ' + self.token})
        r = r.json()
        return r['success']

    def get_assets_traded(self):
        ''' Retrieves details on traded assets through list of dictionaries with following keys: 
                'name', 'altName', 'code', 'id', 'rank', 'buy', 'sell', 'spread', 'volume24H', 'marketCap'
            Buy and sell values are provided in relation to AUD$  '''
        return self.do_request_get(URL+'markets/info/basic/')
        
        # TODO: Detail request obtains extensive details on traded assets through list of dictionaries with key 'name', 'id', 'description', 'category', 'mineable', 'spread', 'rank', 'rankSuffix', 'volume', 'urls', 'supply'
        # r = requests.get(URL+'markets/info/detail/')
    
    def get_assets_listed(self):
        ''' Obtains listed assets on exchange through list of dictionaries with following keys:
                'id', 'code', 'name', 'assetType', 'primary', 'secondary', 'deposit_enabled', 'withdraw_enabled',
                'min_deposit', 'min_withdrawal', 'mining_fee', 'tradable', 'min_confirmations', 'price_scale',
                'minimum_order_increment', 'minimum_order', 'minWithdrawalIncrementC', 'minWithdrawalIncrementE',
                'subAssetOf', 'contract', 'assetDepositScale', 'delisting', 'buyDisabled', 'networks' '''
        return self.do_request_get(URL+'markets/assets/')

    def get_balances(self):
        ''' Obtains balances of owned assets through list of dictionaries with following keys
                'assetId', 'availableBalance' '''
        return self.do_request_get(URL_AUTH+'user/balance/', self.token)

    def get_transactions(self):
        ''' Obtains all transactions through list of dictionaries with the following keys:
                'amount': (float) indicates the amount of coins/tokens,
                'trigger': (float) indicates the exchange rate at time of trade,
                'quantity': (float) indicates the value at time of trade in value of primaryAsset / quantityAsset,
                'primaryAsset': (int) primaryAsset id,
                'quantityAsset': (int) unit of quantity,
                'asset': (string) indicating the asset by it's ID,
                'updated': (int) ??,
                'actionType': (string) type of transaction,
                'status': (string) result of transaction '''
        return self.do_request_get(URL_AUTH+'history/all/', self.token)  #type/assetId/?limit=&page=&sortBy=

    def parse_balances(self, currency='USDT'):
        ''' Creates overview of current balances > 0 and calculates total value. Overview is printed to console. '''
        balances = []
        currency_ratio_id     = 1
        currency_ratio_sell   = 1
        
        # Determine conversion factors and check that currency can be shown.
        # Reminder that buy/sell values of assets are provided in relation to AUD$
        for i in self.assets_traded:
            if i['code'] == currency:
                currency_ratio_sell   = float(i['sell'])
                currency_id           = i['id']
        
        for i in self.balances:
            id       = i['assetId']
            bal      = float(i['availableBalance'])
            bought   = 0
            sold     = 0
            complete = False

            if bal > 0:
                for j in self.assets_listed:
                    if j['id'] == id:
                        code = j['code']
                        name = '('+j['name']+')'
                
                        for k in self.assets_traded:
                            if k['id'] == id:
                            
                                # The value of the current holdings is deteremined based on the 'sell' value of the asset in the market. This seems most appropriate.
                                sell = float(k['sell'])
                                val  = bal * sell / currency_ratio_sell
                                
                                # FIXME: The following only works as long as the primary asset type of all transactions is in USD, which seems to be the case but it's NOT a guarantee.
                                for l in self.transactions:
                                    if int(l['asset']) == id:
                                        if l['actionType'] in ('Market Buy', 'Limit Buy', 'Stop Limit Buy') and l['status'] == 'Complete':
                                            bought += (1 + FEE) * l['amount'] * l['trigger'] * self.ratio_aud_usd / currency_ratio_sell
                                        if l['actionType'] in ('Market Sell', 'Limit Sell', 'Stop Limit Sell') and l['status'] == 'Complete':
                                            sold   += (1 - FEE) * l['amount'] / l['trigger'] * self.ratio_aud_usd / currency_ratio_sell
                                
                                complete = True
                                break

            if complete:
                gain = 100 * (val + sold) / bought
                balances.append({'code': code, 'name': name, 'bal': bal, 'val': val, 'sold': sold, 'gain': gain})
                
        return balances


    def parse_transactions(self, currency='USDT'):
        ''' Displays all closed and pending transactions in order (most recent last). '''
        completed = []
        pending   = []

        # FIXME: Transactions seem to be all related to USD. This routine won't work properly if this isn't the case.
        ratio = self.get_ratio(currency, 'USDT')
        if not ratio:
            print('Invalid currency provided')
            return        

        for t in reversed(self.transactions):
            if t['actionType'] not in ('Deposit', 'Withdrawal', 'Dust Sell') and t['status'] != 'Failed':
                
                for j in self.assets_traded:
                    if j['id'] == int(t['asset']):
                        code = j['code']

                # FIXME: Sometimes amount is in float, sometimes in string. No idea why. Question for Swyftx
                amount = float(t['amount'])

                # FIXME: The following only works as long as the primary asset type of all transactions is in USD. 
                if t['actionType'] in ('Market Sell', 'Limit Sell', 'Stop Limit Sell'):
                    trans_value = amount / t['trigger']
                    fee = trans_value * FEE
                    rec_value = trans_value - fee
                elif t['actionType'] in ('Market Buy', 'Limit Buy', 'Stop Limit Buy'):
                    rec_value = amount * t['trigger']
                    fee = rec_value * FEE
                    trans_value = rec_value + fee
                
                trans_value *= ratio
                fee         *= ratio
                rec_value   *= ratio
                trigger      = t['trigger'] / ratio
                
                if t['status'] == 'Complete':
                    completed.append({'code': code, 'type': t['actionType'], 'amount': amount, 'trans_value': trans_value, 'fee': fee, 'rec_value': rec_value})

                else:
                    pending.append({'code': code, 'type': t['actionType'], 'amount': amount, 'trigger': (1/trigger), 'rec_value': rec_value})
        
        return completed, pending


class Data():
    def __init__(self):
        self.balances               = []
        self.transactions_pending   = []
        self.transactions_completed = []
    
    def add_balances(self, balances):
        existing_codes = {}
        for i in range(len(self.balances)):
            j = self.balances[i]
            existing_codes[j['code']] =  i
        for i in balances:
            if i['code'] not in existing_codes.keys():
                self.balances.append(i)
            else:
                j = existing_codes[i['code']]
                self.balances[j]['bal']  += i['bal']
                self.balances[j]['val']  += i['val']
                self.balances[j]['sold'] += i['sold']
                self.balances[j]['gain'] += i['gain']
    
    def add_transactions_pending(self, transactions):
        self.transactions_pending += transactions
    
    def add_transactions_completed(self, transactions):
        self.transactions_completed += transactions
    

class Output():
    def __init__(self, data):
        self.data = data
        
    def print_balances(self, currency):
        total_val = 0
        temp = 'Value ('+currency+')'
        print(f'\nCode   (Name)                    |         Balance  | {temp:>14}  |           Sold  |  Total gain')
        print('---------------------------------+------------------+-----------------+-----------------+-------------')
        for i in self.data.balances:       
            print(f"{i['code']:6s} {i['name']:26s}|   {i['bal']:>13.4f}  |  {i['val']:>13.4f}  |  {i['sold']:>13.4f}  |    {i['gain']:>7.2f}%")
            total_val += i['val']

        print(f'\nTotal portfolio value:                              {total_val:>14.2f}')

    def print_transactions(self, currency):
        ''' Displays all closed and pending transactions in order (most recent last). '''
        print(f'\nTransaction history (in {currency}):\n')
        print(f'  Code |     Action Type |        Amount |   Trans Value |           Fee |  Actual Value')
        print(f'-------+-----------------+---------------+---------------+---------------+---------------')
        for i in self.data.transactions_completed:
            print(f"{i['code']:>6s} | {i['type']:>15s} | {i['amount']:>13.4f} | {i['trans_value']:>13.4f} | {i['fee']:>13.4f} | {i['rec_value']:>13.4f}")
            
        print(f'\nTransactions pending (in {currency}):\n')
        print(f'  Code |     Action Type |        Amount |       Trigger |   Actual Value')
        print(f'-------+-----------------+---------------+---------------+----------------')
        for i in self.data.transactions_pending:
            print(f"{i['code']:>6s} | {i['type']:>15s} | {i['amount']:>13.4f} | {i['trigger']:>13.4f} | {i['rec_value']:>13.4f}")

    def export_transactions(self):
        ''' Placeeholder function for export function '''
        pass

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--demo', help='uses demo mode', action='store_true')
    parser.add_argument('-b', '--balance', help='displays current balance', action='store_true')
    parser.add_argument('-t', '--transactions', help='displays completed and pending transactions', action='store_true')
    parser.add_argument('-c', '--currency', type = str, help="sets the currency (USDT default)")
    args = parser.parse_args()
    currency = args.currency           
    
    URL = 'https://api.swyftx.com.au/'
    if not args.demo:
        URL_AUTH = 'https://api.swyftx.com.au/'
    else:
        URL_AUTH = 'https://api.demo.swyftx.com.au/'
    
    if not get_status():
        print(f'Can\'t connect to endpoint. Please check connection.')
        exit(2)
    
    s = Swyftx()
    d = Data()
    o = Output(d)
            
    # The currency default needs to be set here as well as the CLI can be set to None
    if not currency:
        currency = 'USDT'
    if not s.exists_currency(currency):
        print(f'Unknown currency selected')
        exit(2)

    if not s.status:
        print(f'Could not establish connection to Swyftx API')
        exit(2)
    else:
        print(f'Connection to Swyftx API established')
                
        if args.balance:
            b = s.parse_balances(currency)
            d.add_balances(b)
            o.print_balances(currency)       
        if args.transactions:
            c, p = s.parse_transactions(currency)
            d.add_transactions_pending(p)
            d.add_transactions_completed(c)
            o.print_transactions(currency)       
        if s.logout():
            print(f'\nSuccessfully logged out')
        else:
            print(f'\nNot successfully logged out')
