import routeros_api
connection = routeros_api.RouterOsApiPool('192.168.200.1', 'admin', '555288', plaintext_login=True)
api = connection.get_api()
nat_rules_api = api.get_resource('/interface/bridge/host')
nat_rules = nat_rules_api.get()
print(nat_rules)