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
            actual_qty = 0
            
            # Search for MOs where this product is the main product
            main_product_mos = self.env['mrp.production'].search([
                ('product_id', '=', line.product_id.id),
                ('state', '=', 'done'),
                ('date_start', '>=', line.date),
                ('date_start', '<', line.date + datetime.timedelta(days=1)),
            ])
            actual_qty += sum(mo.qty_produced for mo in main_product_mos)
            
            # Search for MOs where this product appears as a by-product in finished moves
            byproduct_moves = self.env['stock.move'].search([
                ('product_id', '=', line.product_id.id),
                ('state', '=', 'done'),
                ('move_dest_ids.production_id', '!=', False),
                ('date', '>=', line.date),
                ('date', '<', line.date + datetime.timedelta(days=1)),
            ])
            actual_qty += sum(move.product_uom_qty for move in byproduct_moves)
            
            # Calculate downtime for relevant MOs
            downtime = 0
            all_relevant_mos = main_product_mos + byproduct_moves.mapped('move_dest_ids.production_id')
            for mo in all_relevant_mos:
                if hasattr(mo, 'x_studio_one2many_field_RcsDL'):
                    downtime += sum(rec.x_studio_downtimemin for rec in mo.x_studio_one2many_field_RcsDL if hasattr(rec, 'x_studio_downtimemin'))

            line.actual_quantity = actual_qty
            line.achievement = (actual_qty / line.planned_quantity) if line.planned_quantity > 0 else 0
            line.difference = (actual_qty - line.planned_quantity) if line.planned_quantity > 0 else 0
