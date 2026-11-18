"""Shared raw CSV contracts; IDs are nonnegative, including visitor ID zero."""

EVENT_WEIGHTS = {"view": 1.0, "addtocart": 3.0, "transaction": 5.0}
AVAILABILITY_FILES = ("item_properties_part1.csv", "item_properties_part2.csv")
PROPERTY_COLUMNS = ("timestamp", "itemid", "property", "value")
SCHEMAS = {
    "events.csv": ("timestamp", "visitorid", "event", "itemid", "transactionid"),
    **{name: PROPERTY_COLUMNS for name in AVAILABILITY_FILES},
    "category_tree.csv": ("categoryid", "parentid"),
}
INTEGER_MAX = {
    "timestamp": 2**63 - 1,
    "visitorid": 2**31 - 1,
    "itemid": 2**31 - 1,
    "transactionid": 2**63 - 1,
    "categoryid": 2**31 - 1,
    "parentid": 2**31 - 1,
}
NULLABLE = {"transactionid", "parentid"}
