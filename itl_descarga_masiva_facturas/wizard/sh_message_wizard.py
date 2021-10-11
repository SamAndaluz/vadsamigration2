# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import api, fields, models, _

class sh_message_wizard(models.TransientModel):
    _name="sh.message.wizard"
    _description = "Message wizard to display warnings, alert ,success messages"      
    
    def get_default(self):
        if self.env.context.get("message",False):
            return self.env.context.get("message")
        return False 

    name=fields.Text(string="Message",readonly=True,default=get_default)
    
    #@api.multi
    def close_wizard(self):
        if self.env.context.get('invoice_ids'):
            view = 'account.action_move_in_invoice_type'
            #view = 'account.action_invoice_tree2'
            action = self.env.ref(view).read()[0]
            action['domain'] = [('id', 'in', self.env.context.get('invoice_ids'))]
            return action  
            #self.env['xml.import.wizard'].action_view_invoices(self.env.context.get('invoice_ids'))
        else:
            return
    