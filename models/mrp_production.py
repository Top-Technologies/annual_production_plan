from odoo import models, fields, api

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    x_annual_plan_qty = fields.Float(
        string='Annual Plan Quantity',
        help='Quantity to be used for annual production plan calculation',
        copy=False
    )

    def action_copy_qty_producing(self):
        """Manual action to copy qty_producing to x_annual_plan_qty"""
        for production in self:
            production.x_annual_plan_qty = production.qty_producing
            print(f"COPIED: MO {production.name}, qty_producing={production.qty_producing} -> x_annual_plan_qty={production.x_annual_plan_qty}")
        return True
