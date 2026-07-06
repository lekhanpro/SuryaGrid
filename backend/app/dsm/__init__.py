"""Advanced, configurable Deviation Settlement Mechanism (DSM) engine.

DSM rules vary by country, region, grid code, regulator, generator type, installed
capacity, and time block - so this package models DSM as configurable *rule
profiles* (region + regulator + denominator + tolerance band + slab bands), never
a single hardcoded universal value. See docs/DSM_RULE_SOURCES.md.
"""
