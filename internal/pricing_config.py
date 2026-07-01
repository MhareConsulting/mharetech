"""Per-product pricing configuration for the live calculator.

Each config is serialised to JSON into the pricing page and read by
static/js/pricing.js. Two modes:
  hardware — myTrack: per-vehicle-group hardware BOM + install + monthly run cost.
  software — myRoutes: per-vehicle software subscription + once-off setup.

All money values are ILLUSTRATIVE placeholders — edited in-browser to real costs.
"""

MYTRACK_PRICING = {
    'slug': 'mytrack',
    'name': 'myTrack',
    'mode': 'hardware',
    'currency': 'R',
    'result_labels': {'subtotal': 'Hardware + installation', 'fee': 'Account initiation fee'},
    'assumptions': [
        {'title': 'Hardware (R / item)', 'items': [
            {'key': 'tracker', 'label': 'FMB tracker', 'value': 1200},
            {'key': 'can', 'label': 'CAN adapter (LV-CAN200)', 'value': 1800},
            {'key': 'obd', 'label': 'OBD harness', 'value': 350},
            {'key': 'probe', 'label': 'LLS fuel probe', 'value': 2200},
            {'key': 'panic', 'label': 'Panic button', 'value': 180},
            {'key': 'immob', 'label': 'Immobiliser / cut-off', 'value': 450},
            {'key': 'rfid', 'label': 'RFID / iButton', 'value': 320},
            {'key': 'temp', 'label': 'Temp sensor', 'value': 650},
            {'key': 'batt', 'label': 'Backup battery', 'value': 280},
            {'key': 'sim', 'label': 'SIM (once-off)', 'value': 50},
            {'key': 'cable', 'label': 'Harness / cabling', 'value': 150},
        ]},
        {'title': 'Installation & initiation (R)', 'items': [
            {'key': 'lab_basic', 'label': 'Install — Basic /veh', 'value': 250},
            {'key': 'lab_standard', 'label': 'Install — Standard /veh', 'value': 650},
            {'key': 'lab_advanced', 'label': 'Install — Advanced /veh', 'value': 1400},
            {'key': 'init', 'label': 'Account initiation fee', 'value': 3500},
        ]},
        {'title': 'Monthly run cost (R / unit / mo)', 'items': [
            {'key': 'm_sim', 'label': 'SIM / data', 'value': 35},
            {'key': 'm_host', 'label': 'Hosting', 'value': 18},
            {'key': 'm_lic', 'label': 'Software licence', 'value': 25},
            {'key': 'm_support', 'label': 'Support reserve', 'value': 20},
            {'key': 'm_notif', 'label': 'Notifications', 'value': 12},
            {'key': 'm_api', 'label': 'Map / routing API', 'value': 8},
            {'key': 'm_warranty', 'label': 'Warranty reserve', 'value': 15},
        ]},
        {'title': 'Pricing levers', 'items': [
            {'key': 'margin_pct', 'label': 'Gross margin % (monthly)', 'value': 45, 'pct': True},
            {'key': 'hwmk_pct', 'label': 'Hardware markup %', 'value': 30, 'pct': True},
            {'key': 'insmk_pct', 'label': 'Install markup %', 'value': 20, 'pct': True},
            {'key': 'disc_small', 'label': 'Discount — Small %', 'value': 0, 'pct': True},
            {'key': 'disc_med', 'label': 'Discount — Medium %', 'value': 8, 'pct': True},
            {'key': 'disc_ent', 'label': 'Discount — Enterprise %', 'value': 15, 'pct': True},
        ]},
    ],
    'seed': [
        {'group': 'Long-haul trucks', 'qty': 12, 'source': 'CAN', 'panic': True, 'immob': True, 'rfid': True, 'temp': False, 'batt': True, 'install': 'Standard'},
        {'group': 'Delivery vans', 'qty': 14, 'source': 'OBD', 'panic': True, 'immob': False, 'rfid': True, 'temp': False, 'batt': False, 'install': 'Basic'},
        {'group': 'Reefer trucks', 'qty': 4, 'source': 'CAN', 'panic': True, 'immob': True, 'rfid': True, 'temp': True, 'batt': True, 'install': 'Advanced'},
    ],
}

MYROUTES_PRICING = {
    'slug': 'myroutes',
    'name': 'myRoutes',
    'mode': 'software',
    'currency': 'R',
    'result_labels': {'subtotal': 'Integration (optional)', 'fee': 'Onboarding, data & training'},
    'assumptions': [
        {'title': 'Monthly run cost (R / vehicle / mo)', 'items': [
            {'key': 'm_platform', 'label': 'Platform licence / vehicle', 'value': 120},
            {'key': 'm_host', 'label': 'Hosting', 'value': 15},
            {'key': 'm_api', 'label': 'Map / routing API', 'value': 40},
            {'key': 'm_support', 'label': 'Support reserve', 'value': 25},
            {'key': 'm_notif', 'label': 'Notifications', 'value': 10},
        ]},
        {'title': 'Once-off (R)', 'items': [
            {'key': 'setup', 'label': 'Onboarding / setup', 'value': 6000},
            {'key': 'dataload', 'label': 'Data load & geocoding config', 'value': 3500},
            {'key': 'training', 'label': 'Training', 'value': 2500},
            {'key': 'integration', 'label': 'Integration (if required)', 'value': 8000},
        ]},
        {'title': 'Pricing levers', 'items': [
            {'key': 'margin_pct', 'label': 'Gross margin % (monthly)', 'value': 45, 'pct': True},
            {'key': 'disc_small', 'label': 'Discount — Small %', 'value': 0, 'pct': True},
            {'key': 'disc_med', 'label': 'Discount — Medium %', 'value': 10, 'pct': True},
            {'key': 'disc_ent', 'label': 'Discount — Enterprise %', 'value': 18, 'pct': True},
        ]},
    ],
    'seed': {'vehicles': 20, 'integration': False},
}

PRICING = {MYTRACK_PRICING['slug']: MYTRACK_PRICING, MYROUTES_PRICING['slug']: MYROUTES_PRICING}
