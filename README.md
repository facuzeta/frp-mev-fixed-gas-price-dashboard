## How to run

1. Define a new file ./dashboard_site/dashboard_site/.env  with a new secreate key, for example:


```
DEBUG=on
SECRET_KEY='qflfdt^7lufhf2+zyt6lwvvwlbyd#unv$m2j+xyo#4u&%(#-_b'
```

2. Build and run container: docker-compose up 

3. Populate data: follow instruction from https://github.com/facuzeta/frp-mev-fixed-gas-price-tools/blob/main/populate_data.md

4. Check http://localhost:8000/ 
## TODO:

1. Add apache or nginx for production environment (right now is running with runserver)
