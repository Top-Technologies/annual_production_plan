from odoo import models, fields, api
import datetime

class AnnualProductionPlanLine(models.Model):
    _name = 'annual.production.plan.line'
    _description = 'Annual Production Plan Line'

    plan_id = fields.Many2one('annual.production.plan', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    date = fields.Date(required=True)
    planned_quantity = fields.Float(required=True)
    actual_quantity = fields.Float(readonly=True, compute='compute_actuals', store=True)
    achievement = fields.Float(readonly=True, compute='compute_actuals', store=True)
    difference = fields.Float(readonly=True, compute='compute_actuals', store=True)
    remark = fields.Text()
    invisible_id = fields.Char(default=lambda self: self.env['ir.sequence'].next_by_code('plan.line.invisible'))

    @api.depends('date', 'product_id')
    def compute_actuals(self):
        for line in self:
            # Search for MOs on this date
            mos = self.env['mrp.production'].search([
                ('state', '=', 'done'),
                ('date_start', '>=', line.date),
                ('date_start', '<', line.date + datetime.timedelta(days=1)),
            ])
            
            actual_qty = 0
            for mo in mos:
                # Check if this product is the main product of the MO
                if mo.product_id.id == line.product_id.id:
                    actual_qty += mo.qty_produced
                else:
                    # Only check by-products if this is NOT the main product
                    for move in mo.move_finished_ids:
                        if move.product_id.id == line.product_id.id and move.state == 'done':
                            actual_qty += move.product_uom_qty
            
            # Calculate downtime (not used in current logic but kept for completeness)
            downtime = 0
            for mo in mos:
                if hasattr(mo, 'x_studio_one2many_field_RcsDL'):
                    downtime += sum(rec.x_studio_downtimemin for rec in mo.x_studio_one2many_field_RcsDL if hasattr(rec, 'x_studio_downtimemin'))

            line.actual_quantity = actual_qty
            line.achievement = (actual_qty / line.planned_quantity) if line.planned_quantity > 0 else 0
            line.difference = (actual_qty - line.planned_quantity) if line.planned_quantity > 0 else 0
