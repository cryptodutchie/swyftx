#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import requests

DEMO = 0

if not DEMO:
    URL =      'https://api.swyftx.com.au/'
    URL_AUTH = 'https://api.swyftx.com.au/auth/'
    URL_INFO = 'https://api.swyftx.com.au/info/'
else:
    URL =      'https://api.demo.swyftx.com.au/'
    URL_AUTH = 'https://api.demo.swyftx.com.au/auth/'
    URL_INFO = 'https://api.demo.swyftx.com.au/info/'


def get_key():
    ''' The script requires your API key to be stored in a local file named api_key.dat '''
    f = open("api_key.dat")
    line = f.readline()
    f.close()
    return line.rstrip()

def get_status():
    ''' Checks the connection with the INFO endpoint of the server.
        Result and API version is printed to console. '''
    
    r = requests.get(URL_INFO)
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
        r = requests.post(URL_AUTH+'refresh/', data={'apiKey': get_key()})
        r = r.json()

        if 'accessToken' in r.keys():
            result = r['accessToken']
        else:
            result = None
        return result

    def logout(self):
        ''' Logs out of the server and invalides the current access token. '''
        r = requests.post(URL_AUTH+'logout/', headers={'Authorization': 'Bearer ' + self.token})
        r = r.json()
        return r['success']

    def get_assets_traded(self):
        ''' Retrieves details on traded assets through list of dictionaries with following keys: 
                'name', 'altName', 'code', 'id', 'rank', 'buy', 'sell', 'spread', 'volume24H', 'marketCap' '''
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

    def show_balances(self):
        ''' Creates overview of current balances > $0 and calculates total value. Overview is printed to console. '''
        total_val = 0
        
        for i in self.balances:
            id = i['assetId']
            bal = float(i['availableBalance'])
            complete = False

            if bal > 0:
                for j in self.assets_listed:
                    if j['id'] == id:
                        code = j['code']
                        name = '('+j['name']+')'
                
                        for k in self.assets_traded:
                            if k['id'] == id:
                                sell = float(k['sell'])
                                val  = sell * bal
                                complete = True
                                break

            if complete:
                total_val += val
                print(f'{code:6s} {name:26s}: {bal:>13.4f}  |  {val:>13.4f}')

        print(f'\nTotal portfolio value:                            {total_val:>14.2f}')
    
if __name__ == "__main__":

    if not get_status():
        exit(2)
    
    s = Swyftx()
    if not s.status:
        print(f'Could not establish connection to Swyftx API')
        exit(2)
    else:
        print(f'Connection to Swyftx API established')
        s.show_balances()
        if s.logout():
            print(f'\nSuccessfully logged out')
        else:
            print(f'\nNot successfully logged out')
