odoo.define('shared_barcode.pos', function (require) {
    'use strict';
    
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    
    // Extiende la pantalla de productos para manejar códigos de barras compartidos
    const SharedBarcodePosProductScreen = ProductScreen => 
        class extends ProductScreen {
            async _barcodeProductAction(code) {
                // Primero intentamos el comportamiento estándar
                const result = await super._barcodeProductAction(code);
                
                // Si el código de barras estándar encuentra un producto, usamos ese
                if (result !== null) {
                    return result;
                }
                
                // Si no se encontró, buscamos en la base de datos del POS
                // entre los productos cargados si alguno tiene ese código en su template
                const products = this.env.pos.db.product_by_id;
                
                for (const productId in products) {
                    const product = products[productId];
                    
                    // Verificamos si el producto pertenece a un template que use código compartido
                    // y si el código coincide
                    if (product.barcode === code) {
                        // Si encontramos el producto, lo añadimos al pedido
                        this.currentOrder.add_product(product);
                        return true;
                    }
                }
                
                // Si llegamos aquí, el código no coincide con ningún producto
                return null;
            }
        };
    
    Registries.Component.extend(ProductScreen, SharedBarcodePosProductScreen);
    
    return SharedBarcodePosProductScreen;
});