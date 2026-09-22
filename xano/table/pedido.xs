// Pedidos realizados pelos Clientes.
table PEDIDO {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    decimal total?
    text? nfc_e? filters=trim
    text? cod_entrega? filters=trim
    int cliente_id? {
      table = "CLIENTE"
    }
  
    int status_pedido_id?=1 {
      table = "STATUS_PEDIDO"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "nfc_e", op: "desc"}]}
  ]

  guid = "7kv8_dOIq5wV1cM7Q7g7TVJilWE"
}