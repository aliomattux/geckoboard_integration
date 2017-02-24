from openerp.osv import osv, fields

class GeckoboardWidget(osv.osv):
    _name = 'gecko.board.widget'
    _columns = {
	'name': fields.char('Widget Name'),
	'short_time': fields.boolean('24 hour MAX RAG'),
	'long_time': fields.boolean('Long MAX RAG'),
	'function_name': fields.char('Function Name'),
	'widget_key': fields.char('Widget Key'),
	'widget_url': fields.char('Widget URL'),
        'filtered_statuses': fields.many2many('mage.mapping.order.state', 'geckoboard_widget_mage_status_rel', 'status_id', \
                'widget_id', 'Filtered Statuses'
        ),
        'excluded_shipping_methods': fields.many2many('delivery.carrier', 'geckoboard_widget_delivery_exclusion_rel', 'delivery_id', \
                'widget_id', 'Excluded Shipping Methods'
        ),
        'included_shipping_methods': fields.many2many('delivery.carrier', 'geckoboard_widget_delivery_inclusion_rel', 'delivery_id', \
                'widget_id', 'Included Shipping Methods'
        ),

    }


    def send_widget_update(self, cr, uid, ids, context=None):
	api_obj = self.pool.get('gecko.board.api')
	widget = self.browse(cr, uid, ids[0])
	return getattr(api_obj, widget.function_name)(cr, uid, widget)


    def run_rag_widgets(self, cr, uid, job, context=None):
	ids = self.search(cr, uid, [('function_name', '=', 'generate_and_send_rag_map')])
	for id in ids:
	    self.send_widget_update(cr, uid, [id])
	self.send_widget_update(cr, uid, [6])
	self.send_widget_update(cr, uid, [8])
	self.send_widget_update(cr, uid, [10])
	self.send_widget_update(cr, uid, [15])


    def run_map_widgets(self, cr, uid, job, context=None):
	ids = self.search(cr, uid, [('function_name', '=', 'generate_and_send_customer_map')])
	for id in ids:
	    self.send_widget_update(cr, uid, [id])
