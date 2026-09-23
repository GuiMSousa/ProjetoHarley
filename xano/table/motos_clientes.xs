table motos_clientes {
  auth = false

  schema {
    int id
    int id_cliente {
      table = "clientes"
    }
  
    text modelo filters=trim
    text placa filters=trim
    text chassi filters=trim
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "id_cliente"}]}
    {type: "btree|unique", field: [{name: "placa"}]}
    {type: "btree|unique", field: [{name: "chassi"}]}
  ]

  guid = "LkTvFmt1cGHQD0lLPcb5V-uP1ac"
}