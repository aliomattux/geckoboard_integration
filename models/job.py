from openerp.osv import osv, fields
import requests
from requests.auth import HTTPBasicAuth
import logging
from pprint import pprint as pp
import urllib2
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
_logger = logging.getLogger(__name__)


class GeckoboardApi(osv.osv_memory):
    _name = 'gecko.board.api'

    def backorders_datasets(self, cr, uid, widget, context=None):
	query = "\nSELECT create_date AT TIME ZONE 'UTC' AS created_on, create_date AT TIME ZONE 'UTC' - now() AS delay, origin AS order_number" \
		"\nFROM stock_picking" \
		"\nWHERE backorder_id IS NOT NULL" \
		"\nAND picking_type_id = 2" \
		"\nAND state NOT IN ('cancel', 'draft', 'done')" \
		"\nAND sale IS NOT NULL" \
		"\nORDER BY create_date DESC"
	cr.execute(query)
	results = cr.dictfetchall()
        _logger.info(results)
	new_data = []
	for res in results:
	    res['created_on'] = res['created_on'].strftime('%Y-%m-%d')
	    res['delay'] = str(res['delay'])
	    new_data.append(res)

        dat = json.dumps({'data': new_data})
        upload_response = requests.put(widget.widget_url, data=dat, auth=HTTPBasicAuth(widget.widget_key, False))


    def shipments_month_to_date(self, cr, uid, widget, context=None):
        now = datetime.utcnow()
        eastern = pytz.timezone('US/Eastern')
        utc = pytz.timezone('UTC')
        utc_now = utc.localize(now)
        yesterday = utc_now.astimezone(eastern) - relativedelta(months=1)
        d = yesterday.strftime('%Y-%m-%d')
	query = "SELECT COUNT(DISTINCT picking) FROM stock_out_package WHERE create_date > '%s'"%d
	title = 'Total Orders Shipped Last Month to Date'
	return self.number_widget(cr, uid, widget, query, title)


    def shipments_today(self, cr, uid, widget, context=None):
        now = datetime.utcnow()
        eastern = pytz.timezone('US/Eastern')
        utc = pytz.timezone('UTC')
        utc_now = utc.localize(now)
        yesterday = utc_now.astimezone(eastern)
        d = yesterday.strftime('%Y-%m-%d')
	query = "SELECT COUNT(DISTINCT picking) FROM stock_out_package WHERE create_date > '%s'"%d
	title = 'Total Orders Shipped Today'
	return self.number_widget(cr, uid, widget, query, title)


    def orders_on_hold(self, cr, uid, widget, context=None):
        now = datetime.utcnow()
        eastern = pytz.timezone('US/Eastern')
        utc = pytz.timezone('UTC')
        utc_now = utc.localize(now)
        yesterday = utc_now.astimezone(eastern)
        d = yesterday.strftime('%Y-%m-%d')
	query = "SELECT COUNT(id) FROM sale_order WHERE mage_custom_status IN ('holded', 'Shipping_HOLD')"
	title = 'Orders on Hold'
	return self.number_widget(cr, uid, widget, query, title)


    def prepare_pie_chart(self, cr, uid, widget, context=None):

        now = datetime.utcnow()
        eastern = pytz.timezone('US/Eastern')
        utc = pytz.timezone('UTC')
        utc_now = utc.localize(now)
        yesterday = utc_now.astimezone(eastern) - timedelta(days=1)
        d = yesterday.strftime('%Y-%m-%d')
	query = "SELECT count(sale.carrier_id) AS channel_count, carrier.channel_name, carrier.channel_color" \
	"\nFROM sale_order sale" \
	"\nJOIN delivery_carrier carrier ON (sale.carrier_id = carrier.id)" \
	"\nWHERE sale.create_date AT TIME ZONE 'UTC' > '%s'" \
	"\nGROUP BY carrier.channel_name, carrier.channel_color" % d

	cr.execute(query)
	results = cr.dictfetchall()
        title = 'Orders by Channel'

        data = {'item': []}
	for res in results:
	    data['item'].append(
                {
		"value": res['channel_count'],
		"label": res['channel_name'],
		"color": res['channel_color']
		},
	    )

        payload = {
                   'api_key': widget.widget_key,
                   'data': data
        }

        json_data = json.dumps(payload)
        req = urllib2.Request(widget.widget_url, json_data, {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        response = f.read()
        f.close()

        return True


    def orders_in_picking(self, cr, uid, widget, context=None):
	query = "SELECT COUNT(id) FROM sale_order WHERE mage_custom_status = 'Picking'"
        title = 'Orders in Picking'
        return self.number_widget(cr, uid, widget, query, title)


    def number_widget(self, cr, uid, widget, query, title):
	cr.execute(query)
	results = cr.fetchone()
	number = int(results[0])

        data = {
          "item": [
            {
              "value": number,
              "text": title
            }
          ]
        }

	return self.send_geckoboard_data(cr, uid, data, widget.widget_key, widget.widget_url)


    def get_long_time(self, days):
        now = datetime.utcnow()
        eastern = pytz.timezone('US/Eastern')
        utc = pytz.timezone('UTC')
        utc_now = utc.localize(now)
	
        yesterday = utc_now.astimezone(eastern)
	yesterday -= timedelta(days=days)

#	while yesterday.strftime("%A") not in DAYS:
#	    yesterday -= timedelta(days=1)

        return yesterday.strftime('%Y-%m-%d')


    def get_negative_metric(self, cr, uid, date_before, date_onorafter, \
		inclusions, exclusions, statuses
	):

        query = "SELECT count(id) FROM sale_order WHERE mage_custom_status IN (%s)" % statuses

	if date_before:
            query += "\nAND create_date AT TIME ZONE 'UTC' < '%s'" % date_before

	#If not newer than x date
        if date_onorafter:
	    query += "\nAND create_date AT TIME ZONE 'UTC' > '%s'" % date_onorafter

	if inclusions:
	    query += "\nAND carrier_id IN (%s)" % inclusions
	if exclusions:
	    query += "\nAND carrier_id NOT IN (%s)" % exclusions

	cr.execute(query)
	result = cr.fetchone()
	return int(result[0])


    def generate_and_send_rag_map(self, cr, uid, widget, context=None):
	#No Newer Order Than: number of days aged - 1 because date < is 11:59 the day prior
	#No Order Older than: number of days back because date > is 12:01 on day and newer
	filtered = False
	inclusions = False
	exclusions = False

	if widget.filtered_statuses:
	    filtered = [str(f.mage_order_status) for f in widget.filtered_statuses]
	    filtered = ", ".join( repr(e) for e in filtered )
	if widget.included_shipping_methods:
	    inclusions = [str(i.id) for i in widget.included_shipping_methods]
	    inclusions = ", ".join( repr(e) for e in inclusions )
	if widget.excluded_shipping_methods:
	    exclusions = [str(e.id) for e in widget.excluded_shipping_methods]
	    exclusions = ", ".join( repr(e) for e in exclusions )

	if widget.short_time:
	    #R
	    date_before_super_late = self.get_long_time(1)
	    date_onorafter_super_late = False

	    #A-Not Applicable
	    number_late = 0

	    #G
	    date_before_green = False
	    date_onorafter_green = self.get_long_time(1)

	    text_green = '24 Hrs'
	    text_amber = 'N/A'
	    text_red = 'LATE'

	elif widget.long_time:
            #R
            date_before_super_late = self.get_long_time(15)
            date_onorafter_super_late = False

            #A
            date_before_late = self.get_long_time(7)
            date_onorafter_late = self.get_long_time(15)

            #G
            date_before_green = False
            date_onorafter_green = self.get_long_time(7)

	    text_green = '0-7 Days'
	    text_amber = '8-15 Days'
	    text_red = 'LATE'

            number_late = self.get_negative_metric(cr, uid, date_before_late, date_onorafter_late, \
                inclusions, exclusions, filtered
            )

	else:
	    #R
	    date_before_super_late = self.get_long_time(4)
	    date_onorafter_super_late = False

	    #A
	    date_before_late = self.get_long_time(2)
	    date_onorafter_late = self.get_long_time(4)

	    #G
	    date_before_green = False
	    date_onorafter_green = self.get_long_time(1)


            text_green = '24 Hrs'
            text_amber = '3-4 Days'
            text_red = '5 Days'

	    number_late = self.get_negative_metric(cr, uid, date_before_late, date_onorafter_late, \
		inclusions, exclusions, filtered
	    )

	number_green = self.get_negative_metric(cr, uid, date_before_green, date_onorafter_green, \
		inclusions, exclusions, filtered
	)

	number_super_late = self.get_negative_metric(cr, uid, date_before_super_late, \
		date_onorafter_super_late, inclusions, exclusions, filtered
	)
	
        data = {
            "item": [
                { "text": text_red, "value": number_super_late },
                { "text": text_amber, "value": number_late },
                { "text": text_green, "value": number_green }
            ]
        }

	return self.send_geckoboard_data(cr, uid, data, widget.widget_key, widget.widget_url)


    def generate_and_send_customer_map(self, cr, uid, widget, context=None):
	data = self.customer_map_sql_query(cr, uid)
#	if not data:
#	    return True
	prepared_vals = self.generate_counts(cr, uid, data)
	self.send_geckoboard_data(cr, uid, prepared_vals['data'], widget.widget_key, widget.widget_url)


    def send_geckoboard_data(self, cr, uid, raw_data, api_key, url):
	req = {'data': raw_data, 'api_key': api_key}
	data = json.dumps(req)
	result = requests.post(url, data=data, headers={"Content-Type":"application/json"})


    def customer_map_sql_query(self, cr, uid):
        now = datetime.utcnow()
        eastern = pytz.timezone('US/Eastern')
        utc = pytz.timezone('UTC')
        utc_now = utc.localize(now)
        yesterday = utc_now.astimezone(eastern)
        d = yesterday.strftime('%Y-%m-%d')

        query = "SELECT state.code AS region_code, country.code AS country_code, partner.city AS city_name" \
	"\nFROM stock_picking picking" \
        "\nJOIN sale_order sale ON (picking.sale = sale.id)" \
        "\nJOIN res_partner partner ON (sale.partner_shipping_id = partner.id)" \
        "\nJOIN res_country_state state ON (partner.state_id = state.id)" \
        "\nJOIN res_country country ON (partner.country_id = country.id)" \
	"WHERE picking.id IN (SELECT DISTINCT picking FROM stock_out_package WHERE create_date" \
	" AT TIME ZONE 'UTC' > '%s')" % d
	cr.execute(query)
	return cr.dictfetchall()


    def generate_counts(self, cr, uid, location_data, context=None):
        prepared_vals = []

  #      counts = {'0000FF': 0,
   #               '663300': 0,
    #              '990099': 0,
     #             'CC3300': 0,
#                  '00CCFF': 0,
  #                '33CC33': 0
   #     }

        for location in location_data:
#            color = location['color']
 #           counts[color] += 1
            prepared_vals.append({'city': location})

        return {'data': {'points': {'point': prepared_vals}}, }#'counts':counts}
