from openerp.osv import osv, fields
import json
import urllib2

#API_KEY = '59182-1200c657-0552-4618-b8f8-693e5bc8d4c5'
API_KEY = 'c00ad400864e2dbebc18df4e16090b89'
URL = 'https://push.geckoboard.com/v1/send/59182-b6678363-7640-4f4e-a67b-294a339bbd91'


class GeckoBoard(osv.osv_memory):
    _name = 'gecko.board.api'

    def prepare_and_send_map_data(self, cr, uid, ids, context=None):
        map_data = self.gather_map_data(cr, uid)
	print 'Map Data', map_data
	if map_data:
	    prepared_vals = self.prepare_map(cr, uid, map_data)
	 #   self.prepare_pie_chart(cr, uid, prepared_vals['counts'])
	    self.send_geckoboard_data(cr, uid, prepared_vals['data'], API_KEY, URL)

	return True


    def gather_map_data(self, cr, uid):
	tran_obj = self.pool.get('stock.transaction')
	entity_obj = self.pool.get('entity.address')

	entity_fields = ['city', 'country_code', 'state']

	query = "SELECT entity.state AS region_code, entity.city AS city_name, " \
		 "entity.country_code, dept.color" \
		 "\nFROM entity_address entity" \
		 "\nJOIN stock_transaction fulfillment ON (entity.id = fulfillment.shipping_address)" \
		 "\nJOIN department dept ON (fulfillment.department = dept.id)"

	cr.execute(query)
	return cr.dictfetchall()


    def prepare_pie_chart(self, cr, uid, counts):
        URL = 'https://push.geckoboard.com/v1/send/59182-f33f73a7-d675-4be1-9f57-ccdfe1c4d63f'
	data = { 
		"item": [ 
		{ 
		"value": counts['0000FF'], 
		"label": "Fridge Filters",
		"colour": "0000FF" 
		}, 
		{ 
		"value": counts['663300'], 
		"label": "Water Filters", 
		"colour": "663300" 
		}, 
		{ 
		"value": counts['990099'], 
		"label": "Discount Filter Store", 
		"colour": "990099" 
		}, 
		{
		"value": counts['CC3300'],
		"label": "InstaPure",
		"colour": "CC3300"
		},
		{ 
		"value": counts['00CCFF'], 
		"label": "Commercial", 
		"colour": "00CCFF" 
		},
		{
		"value": counts['33CC33'],
		"label": "Everything Else",
		"colour": "33CC33"
		}
		] 
		}


        payload = {
                   'api_key':API_KEY,
                   'data': data
        }

        json_data = json.dumps(payload)
        print data
        req = urllib2.Request(URL, json_data, {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        response = f.read()
        print response
        f.close()

        return True

    def prepare_map(self, cr, uid, location_data, context=None):
	prepared_vals = []

	counts = {'0000FF': 0, 
		  '663300': 0,
		  '990099': 0,
		  'CC3300': 0,
		  '00CCFF': 0,
		  '33CC33': 0
	}

	for location in location_data:
	    color = location['color']
	    counts[color] += 1
	    prepared_vals.append({'city': location})

	return {'data': {'points': {'point': prepared_vals}}, 'counts':counts}


    def send_geckoboard_data(self, cr, uid, data, api_key, url):

	payload = {
		   'api_key':API_KEY,
		   'data': data
	}

	json_data = json.dumps(payload)
	print data
	req = urllib2.Request(URL, json_data, {'Content-Type': 'application/json'})
	f = urllib2.urlopen(req)
	response = f.read()
	print response
	f.close()
