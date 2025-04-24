from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    shared_barcode = fields.Char(
        string='Código de Barras Compartido',
        help='Este código de barras será compartido entre todas las variantes de este producto'
    )
    
    use_shared_barcode = fields.Boolean(
        string='Usar código de barras compartido',
        help='Si está marcado, todas las variantes usarán el mismo código de barras'
    )
    
    @api.onchange('use_shared_barcode')
    def _onchange_use_shared_barcode(self):
        """Actualiza las variantes cuando se activa el código de barras compartido"""
        if self.use_shared_barcode and self.shared_barcode:
            # Si activamos el código compartido, actualizamos todas las variantes
            for variant in self.product_variant_ids:
                variant.barcode = self.shared_barcode
        elif not self.use_shared_barcode:
            # Si desactivamos el código compartido, limpiamos los códigos de barras de las variantes
            for variant in self.product_variant_ids:
                variant.barcode = False
    
    @api.onchange('shared_barcode')
    def _onchange_shared_barcode(self):
        """Actualiza las variantes cuando cambia el código de barras compartido"""
        if self.use_shared_barcode and self.shared_barcode:
            for variant in self.product_variant_ids:
                variant.barcode = self.shared_barcode


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # Sobrescribimos el método de restricción de unicidad del código de barras
    _sql_constraints = [
        ('barcode_uniq', "CHECK(1=1)", "Un código de barras puede ser compartido entre variantes del mismo producto."),
    ]
    
    @api.constrains('barcode')
    def _check_barcode_uniqueness(self):
        """Permite códigos de barras duplicados solo entre variantes del mismo producto"""
        for product in self:
            if not product.barcode:
                continue
                
            # Si el producto usa código compartido, permitimos duplicados dentro del mismo template
            if product.product_tmpl_id.use_shared_barcode:
                continue
                
            # Buscamos productos con el mismo código de barras pero que no sean variantes del mismo template
            domain = [
                ('barcode', '=', product.barcode),
                ('id', '!=', product.id),
                '|',
                ('product_tmpl_id', '!=', product.product_tmpl_id.id),
                ('product_tmpl_id.use_shared_barcode', '=', False)
            ]
            if self.search_count(domain) > 0:
                raise ValidationError(_(
                    'El código de barras %s ya está siendo utilizado por otro producto que no es una variante del mismo template.'
                ) % product.barcode)


# Clase para extender la búsqueda de productos por código de barras
class PosSession(models.Model):
    _inherit = 'pos.session'
    
    def _loader_params_product_product(self):
        """Extender el cargador de productos para incluir información sobre el código compartido"""
        result = super()._loader_params_product_product()
        if 'search_params' in result and 'fields' in result['search_params']:
            if 'product_tmpl_id' not in result['search_params']['fields']:
                result['search_params']['fields'].append('product_tmpl_id')
        return result


# Sobrescribir la búsqueda de productos por código de barras en el POS
class PosConfig(models.Model):
    _inherit = 'pos.config'


# Método principal para buscar productos por código de barras
class BarcodeRule(models.Model):
    _inherit = 'barcode.rule'
    
    def _get_product_variant_from_barcode(self, barcode):
        """Sobrescribe el método estándar para buscar también en shared_barcode"""
        # Intenta con el comportamiento estándar primero
        product = super()._get_product_variant_from_barcode(barcode)
        
        if product:
            return product
            
        # Si no se encuentra, buscar en el shared_barcode de las plantillas
        template = self.env['product.template'].search([
            ('shared_barcode', '=', barcode),
            ('use_shared_barcode', '=', True)
        ], limit=1)
        
        if template and template.product_variant_ids:
            # Si hay solo una variante, la devolvemos
            if len(template.product_variant_ids) == 1:
                return template.product_variant_ids[0]
            
            # Si hay múltiples variantes y todas están disponibles en el POS,
            # devolvemos la primera por simplicidad
            variants_in_pos = template.product_variant_ids.filtered(
                lambda v: v.available_in_pos
            )
            
            if variants_in_pos:
                return variants_in_pos[0]
        
        return None


# Extender el parseador de códigos de barras
class BarcodeNomenclature(models.Model):
    _inherit = 'barcode.nomenclature'
    
    def parse_barcode(self, barcode):
        """Sobrescribe el método de análisis de códigos de barras para buscar en shared_barcode"""
        result = super().parse_barcode(barcode)
        
        # Si no se encontró un producto, intentar con el shared_barcode
        if result['type'] == 'error':
            template = self.env['product.template'].search([
                ('shared_barcode', '=', barcode),
                ('use_shared_barcode', '=', True)
            ], limit=1)
            
            if template and template.product_variant_ids:
                variant = template.product_variant_ids[0]
                return {
                    'encoding': 'barcode',
                    'type': 'product',
                    'value': barcode,
                    'data': variant,
                }
        
        return result