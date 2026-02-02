import routeros_api
connection = routeros_api.RouterOsApiPool('192.168.88.1', 'admin', 'Admin.555288', plaintext_login=True)
api = connection.get_api()

poe_interface = api.get_resource('/interface/ethernet/poe')
poe_interface.set(id='ether5', poe_out='auto-on')
print(poe_interface.get())

connection.disconnect()
