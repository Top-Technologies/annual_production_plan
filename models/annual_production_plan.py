from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta

class AnnualProductionPlan(models.Model):
    _name = 'annual.production.plan'
    _description = 'Annual Production Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True)
    product_id = fields.Many2one(
        'product.product', 
        string='Product',
        # domain="[('type', '=', 'product')]",
        required=True
    )
    planned_by_id = fields.Many2one(
        'res.users', 
        default=lambda self: self.env.user,
        required=True
    )

    approver_ids = fields.Many2many(
        'res.users',
        'annual_plan_approver_rel',
        'plan_id', 'user_id',
        string='Approvers',
        required=True
    )

    approved_by_ids = fields.Many2many(
        'res.users',
        'annual_plan_approved_by_rel',
        'plan_id', 'user_id',
        string='Approved By',
        readonly=True
    )

    # CHANGED TO DATETIME
    start_date = fields.Datetime(string="Planned Start", required=True)
    end_date = fields.Datetime(string="Planned End", required=True)

    daily_production_plan = fields.Float(
        string="Daily Production Target",
        required=True
    )

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done')
    ], default='draft', tracking=True)

    line_ids = fields.One2many(
        'annual.production.plan.line',
        'plan_id',
        string='Daily Plans'
    )

    #FILTERS
    filter_start_date = fields.Date(string="Show From")
    filter_end_date = fields.Date(string="Show To")

    filtered_planned_qty = fields.Float(
    string="Filtered Planned Qty",
    compute="_compute_filtered_totals"
    )

    filtered_actual_qty = fields.Float(
        string="Filtered Actual Qty",
        compute="_compute_filtered_totals"
    )

    filtered_achievement = fields.Float(
        string="Filtered Achievement (%)",
        compute="_compute_filtered_totals"
    )

    filtered_difference = fields.Float(
        string="Filtered Difference",
        compute="_compute_filtered_totals"
    )



    # TOTALS
    total_planned_qty = fields.Float(
        string="Total Planned Quantity",
        compute="_compute_totals",
        store=True
    )

    total_actual_qty = fields.Float(
        string="Total Actual Quantity",
        compute="_compute_totals",
        store=True
    )

    total_achievement = fields.Float(
        string="Total Achievement (%)",
        compute="_compute_totals",
        store=True
    )
    total_difference = fields.Float(
        string="Total Difference",
        compute="_compute_totals",
        store=True
    )

    @api.depends('line_ids.planned_quantity', 'line_ids.actual_quantity')
    def _compute_totals(self):
        for rec in self:
            planned = sum(rec.line_ids.mapped('planned_quantity'))
            actual = sum(rec.line_ids.mapped('actual_quantity'))
            rec.total_planned_qty = planned
            rec.total_actual_qty = actual
            rec.total_achievement = (actual / planned) if planned else 0.0
            rec.total_difference = (actual - planned) if planned else 0.0


    @api.depends('line_ids.planned_quantity', 'line_ids.actual_quantity',
             'filter_start_date', 'filter_end_date')
    def _compute_filtered_totals(self):
        for rec in self:
            lines = rec.line_ids

            if rec.filter_start_date:
                lines = lines.filtered(lambda l: l.date >= rec.filter_start_date)
            if rec.filter_end_date:
                lines = lines.filtered(lambda l: l.date <= rec.filter_end_date)

            planned = sum(lines.mapped('planned_quantity'))
            actual = sum(lines.mapped('actual_quantity'))

            rec.filtered_planned_qty = planned
            rec.filtered_actual_qty = actual
            rec.filtered_achievement = (actual / planned) if planned else 0.0
            rec.filtered_difference = (actual - planned) if planned else 0.0

    @api.onchange('filter_start_date', 'filter_end_date')
    def _onchange_filter_dates(self):
        domain = []
        if self.filter_start_date:
            domain.append(('date', '>=', self.filter_start_date))
        if self.filter_end_date:
            domain.append(('date', '<=', self.filter_end_date))
        return {'domain': {'line_ids': domain}}


    # VALIDATION
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                if rec.start_date > rec.end_date:
                    raise ValidationError(_("End date cannot be before start date"))
                duration = rec.end_date - rec.start_date
                if duration.days > 366:
                    raise ValidationError(_("Plan duration cannot exceed one year"))

    # ACTIONS
    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft plans can be confirmed.'))
            if not rec.line_ids:
                rec._generate_daily_lines()
            rec.state = 'confirmed'

    def action_approve(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_('Only confirmed plans can be approved.'))
            if self.env.user not in rec.approver_ids:
                raise UserError(_('You are not among the approvers.'))

            rec.approved_by_ids = [(4, self.env.uid)]
            if set(rec.approver_ids.ids).issubset(set(rec.approved_by_ids.ids)):
                rec.state = 'done'

    # GENERATE DAILY LINES (DATETIME SAFE)
    def _generate_daily_lines(self):
        self.ensure_one()
        lines = []
        current = self.start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = self.end_date

        while current <= end:
            # Skip Sundays
            if current.weekday() != 6:
                lines.append((0, 0, {
                    'date': current,
                    'planned_quantity': self.daily_production_plan,
                }))
            current += timedelta(days=1)

        self.write({'line_ids': lines})

    # Recompute actuals by calling line logic
    def action_compute_actuals(self):
        for plan in self:
            plan.line_ids.compute_actuals()
