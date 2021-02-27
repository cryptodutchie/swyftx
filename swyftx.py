#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import requests

DEMO = 0

FEE = 0.006

if not DEMO:
    URL =      'https://api.swyftx.com.au/'
else:
    URL =      'https://api.demo.swyftx.com.au/'


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
        return self.do_request_get(URL+'user/balance/', self.token)

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
        return self.do_request_get(URL+'history/all/', self.token)  #type/assetId/?limit=&page=&sortBy=

    def show_balances(self, currency='USDT'):
        ''' Creates overview of current balances > 0 and calculates total value. Overview is printed to console. '''
        total_val = 0
        currency_ratio_id     = 1
        currency_ratio_sell   = 1
        
        # Determine conversion factors and check that currency can be shown.
        # Reminder that buy/sell values of assets are provided in relation to AUD$
        for i in self.assets_traded:
            if i['code'] == currency:
                currency_ratio_sell   = float(i['sell'])
                currency_id           = i['id']
        
        temp = 'Value ('+currency+')'
        print(f'\nCode   (Name)                    |         Balance  | {temp:>14}  |           Sold  |  Total gain')
        print('---------------------------------+------------------+-----------------+-----------------+-------------')
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
                total_val += val
                gain = 100 * (val + sold) / bought
                print(f'{code:6s} {name:26s}|   {bal:>13.4f}  |  {val:>13.4f}  |  {sold:>13.4f}  |    {gain:>7.2f}%')

        print(f'\nTotal portfolio value:                              {total_val:>14.2f}')

    def show_transactions(self, currency='USDT'):
        ''' Displays all closed and pending transactions in order (most recent last). '''
        completed = []
        pending   = []
        
        # FIXME: Transactions seem to be all related to USD. This routine won't work properly if this isn't the case.
        ratio = self.get_ratio(currency, 'USDT')
        if not ratio:
            print('Invalid currency provided')
            return        

        for t in reversed(s.transactions):
            if t['actionType'] not in ('Deposit', 'Withdrawal') and t['status'] != 'Failed':
                
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
                    completed.append(f"{code:>6s} | {t['actionType']:>15s} | {amount:>13.4f} | {trans_value:>13.4f} | {fee:>13.4f} | {rec_value:>13.4f}")
                else:
                    pending.append(f"{code:>6s} | {t['actionType']:>15s} | {amount:>13.4f} | {1/trigger:>13.4f} |  {rec_value:>13.4f}")

        print(f'\nTransaction history (in {currency}):\n')
        print(f'  Code |     Action Type |        Amount |   Trans Value |           Fee |  Actual Value')
        print(f'-------+-----------------+---------------+---------------+---------------+---------------')
        for i in completed:
            print(i)
            
        print(f'\nTransactions pending (in {currency}):\n')
        print(f'  Code |     Action Type |        Amount |       Trigger |   Actual Value')
        print(f'-------+-----------------+---------------+---------------+----------------')
        for i in pending:
            print(i)

    
if __name__ == "__main__":

    if not get_status():
        exit(2)
    
    s = Swyftx()
    if not s.status:
        print(f'Could not establish connection to Swyftx API')
        exit(2)
    else:
        print(f'Connection to Swyftx API established')
        
        s.show_balances('USDT')
        s.show_transactions('USDT')   
        
        if s.logout():
            print(f'\nSuccessfully logged out')
        else:
            print(f'\nNot successfully logged out')
