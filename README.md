# Project: E-Commerce Cart App (Failure Simulation)

This project simulates:
1. web-app
2. cart-service
3. feature-flag-service (with timeout failure)
4. template-engine And reproduces your exact log flow.

# Structure
fastapi-cart-app/
│
├── app/
│   ├── main.py
│   ├── logging_config.py
│   ├── services/
│   │   ├── cart_service.py
│   │   ├── feature_flag_service.py
│   │   └── template_engine.py
│   └── models.py
│
├── requirements.txt
├── README.md
└── .gitignore