"""
config.py: Configuration values. Secrets to be handled with Secrets Manager
"""

import logging
import socket
import urllib

SKID_NAME = "deq-tanks"

#: Try to get project id from GCP metadata server for hostname. If it's empty or errors out, revert to local hostname
try:
    url = "http://metadata.google.internal/computeMetadata/v1/project/project-id"
    req = urllib.request.Request(url)
    req.add_header("Metadata-Flavor", "Google")
    project_id = urllib.request.urlopen(req).read().decode()
    if not project_id:
        raise ValueError
    HOST_NAME = project_id
    IS_LOCAL_DEV = False
except Exception:
    HOST_NAME = socket.gethostname()
    IS_LOCAL_DEV = True

SENDGRID_SETTINGS = {  #: Settings for SendGridHandler
    "from_address": "noreply@utah.gov",
    "to_addresses": ["ugrc-developers@utah.gov"],
    "prefix": f"{SKID_NAME} on {HOST_NAME}: ",
}
LOG_LEVEL = logging.DEBUG
LOG_FILE_NAME = "log"


class FieldConfig:
    #: field types
    text = "text"
    integer = "integer"
    float = "float"
    date = "date"
    static = "static"
    composite = "composite"

    def __init__(
        self,
        agol_field,
        sf_field,
        alias,
        field_type,
        static_value=None,
        composite_format=None,
        flatten=False,
    ):
        self.agol_field = agol_field
        self.sf_field = sf_field
        self.alias = alias
        self.flatten = flatten

        if field_type not in (
            self.text,
            self.integer,
            self.date,
            self.static,
            self.composite,
            self.float,
        ):
            raise ValueError(f"Invalid field type: {field_type}")
        self.field_type = field_type

        if field_type == self.static and static_value is None:
            raise ValueError("Field type 'static' must have a 'static_value'")
        elif field_type != self.static and static_value is not None:
            raise ValueError("Field type '{field_type}' cannot have a 'static_value'")
        self.static_value = static_value

        if field_type == self.composite and composite_format is None:
            raise ValueError("Field type 'composite' must have a 'composite_format'")
        elif field_type != self.composite and composite_format is not None:
            raise ValueError("Field type '{field_type}' cannot have a 'composite_format'")
        self.composite_format = composite_format

        if flatten and "." not in sf_field:
            raise ValueError(f"Field '{sf_field}' cannot be flattened without a dot")


FACILITIES_API = "services/apexrest/facilities"
FACILITIES_TABLE_NAME = "pst_facilities"
FACILITIES_TITLE = "Utah Petroleum Storage Tanks Facilities"
FACILITIES_FIELDS = (
    #: AGOL field name, Salesforce field name, AGOL Alias, type
    FieldConfig("FACILITYID", "Id", "Facility ID", "text"),
    FieldConfig("NORTHING", "UTMNorthing", "UTM Northing", "integer"),
    FieldConfig("EASTING", "UTMEasting", "UTM Easting", "integer"),
    FieldConfig("TANK", "Tank", "Tank", "text"),
    FieldConfig("SITEDESC", "SiteDesc", "Site Description", "text"),
    FieldConfig("RELEASE", "Release", "Has a Release", "text"),
    FieldConfig("REGAST", "REGAST", "Has State Regulated AST(s)", "text"),
    FieldConfig("LOCSTR", "PhysicalAddressStreet", "Location Address", "text"),
    FieldConfig("LOCSTATE", "PhysicalAddressStateCode", "Location State", "text"),
    FieldConfig("LOCZIP", "PhysicalAddressPostalCode", "Location Zip", "text"),
    FieldConfig("LOCCITY", "PhysicalAddressCity", "Location City", "text"),
    FieldConfig("LOCCOUNTY", "FLCounty", "Location County", "text"),
    FieldConfig("OPENTANK", "OpenTank", "Has an Open Tank", "text"),
    FieldConfig("OPENRELEASE", "OpenRelease", "Has an Open Release", "text"),
    FieldConfig("OPENREGAST", "OpenREGAST", "Has an Open Regulated AST", "text"),
    FieldConfig("MAPLABEL", "MapLabel", "Map Label", "text"),
    FieldConfig("HEALTHDIST", "HealthDistrict", "Health District", "text"),
    FieldConfig("LOCNAME", "FacilityName", "Location Name", "text"),
    FieldConfig("FACILITYDE", "FacilityDescription", "Type of Facility", "text"),
    FieldConfig("DERRID", "AltFacilityID", "Alt Facility ID", "text"),
    FieldConfig("OWNERADDRESS", "AccountShippingStreet", "Owner Address", "text"),
    FieldConfig("OWNERSTATE", "AccountShippingState", "Owner State", "text"),
    FieldConfig("OWNERZIP", "AccountShippingPostalCode", "Owner Postal Code", "text"),
    FieldConfig("OWNERCITY", "AccountShippingCity", "Owner City", "text"),
    FieldConfig("OWNERNAME", "AccountName", "Owner Name", "text"),
)

RELEASES_API = "Release__c"
RELEASES_TABLE_NAME = "pst_facility_releases"
RELEASES_TITLE = "Utah Petroleum Storage Tank Releases"
RELEASES_QUERY = "LPST_List_Override__c = FALSE"
RELEASES_FIELDS = (
    #: AGOL field name, Salesforce field name, AGOL Alias, type
    FieldConfig("FACILITYID", "Alt_Facility_Id__c", "Facility ID", "text"),
    FieldConfig("DERRID", "Release_Id__c", "DERR ID", "text"),
    FieldConfig("PROJECTMAN", "Project_Manager__r.Name", "Project Manager", "text", flatten=True),
    FieldConfig("NOTIFICATI", "Notification_Date__c", "Notification Date", "date"),
    FieldConfig("DATECLOSED", "Date_Closed__c", "Closure Date", "date"),
    FieldConfig("CLOSURETYPE", "Closure_Type__c", "Closure Type", "text"),
    FieldConfig("DEPTHGW", "Depth_to_Groundwater__c", "Depth to GW", "text"),
    FieldConfig("GWFLOWDIR1", "Groundwater_Flow_Direction_1__c", "GW Flow Dir 1", "text"),
    FieldConfig("GWFLOWDIR2", "Groundwater_Flow_Direction_2__c", "GW Flow Dir 2", "text"),
    FieldConfig("PSTFUNDSTA", "PST_Eligibility__c", "PST Eligibility", "text"),
    FieldConfig("PSTFUNDPER", "EAP_Coverage_Percentage__c", "EAP Coverage %", "integer"),
    FieldConfig("DEDUCTIBLE", "EAP_Deductible_Amount__c", "EAP Deductible", "integer"),
    FieldConfig("NFAFORM", "NFA_Form__c", "NFA Form", "text"),
    FieldConfig("MAPLABEL", "MapLabel__c", "Map Label", "text"),
    FieldConfig("BLUESTAKES", "Blue_Stakes__c", "Blue Stakes", "text"),
    FieldConfig("ENVCOV", "Environmental_Covenant__c", "Environmental Covenant", "text"),
    FieldConfig("RESIDUALCONTAMMAP", "Residual_Contamination_Map__c", "Residual Contamination Map", "text"),
    FieldConfig("FEDREG", "Federally_Regulated__c", "Federally Regulated", "text"),
)

TANKS_API = "Tank__c"
TANKS_TABLE_NAME = "pst_facility_tanks"
TANKS_TITLE = "Utah Petroleum Storage Tanks"
TANKS_QUERY = "Tank_Type__c = 'Federally Regulated UST' OR Tank_Type__c = 'State Regulated AST' OR Cert_of_Compliance_in_Force__c = TRUE"
TANKS_FIELDS = (
    #: AGOL field name, Salesforce field name, AGOL Alias, type
    FieldConfig("FACILITYID", "Alt_Facility_ID__c", "Facility ID", "text"),
    FieldConfig("TANKID", "Name", "Tank Number", "text"),
    FieldConfig("ALTTANKID", "Alt_Tank_Id__c", "Tank ID", "text"),
    FieldConfig("TANKTYPE", "Tank_Type__c", "Tank Type", "text"),
    FieldConfig("TANKEMERGE", "Emergency_Gen__c", "Emergency Generator", "text"),
    FieldConfig("TANKSTATUS", "Status__c", "Tank Status", "text"),
    FieldConfig("TANKCAPACI", "Tank_Capacity__c", "Tank Capacity", "integer"),
    FieldConfig("SUBSTANCED", "Substance__c", "Substance", "text"),
    FieldConfig("SUBSTANCET", "Substance_Type__c", "Substance Type", "text"),
    FieldConfig("TANKMATDES", "Tank_Material__c", "Tank Material", "text"),
    FieldConfig("DATEINSTAL", "Date_Installed__c", "Date Installed", "date"),
    FieldConfig("DATECLOSE", "Date_Permanently_Closed__c", "Date Permanently Closed", "date"),
    FieldConfig("INCOMPLIAN", "Cert_of_Compliance_in_Force__c", "Cert. of Compliance in Force", "text"),
    FieldConfig("PST_FUND", "FR_Type__c", "Fr Type", "text"),
)

COMPARTMENTS_API = "Compartment__c"
COMPARTMENTS_TABLE_NAME = "pst_facility_compartments"
COMPARTMENTS_TITLE = "Utah Petroleum Storage Tank Compartments"
COMPARTMENTS_QUERY = "Compartment_Type__c  = 'Federally Regulated UST' OR Compartment_Type__c = 'State Regulated AST' OR Cert_of_Compliance_in_Force__c = TRUE"
COMPARTMENTS_FIELDS = (
    #: AGOL field name, Salesforce field name, AGOL Alias, type
    FieldConfig("FACILITYID", "Alt_Facility_Id__c", "Facility ID", "text"),
    FieldConfig("TANKID", "Tank__r.Name", "Tank ID", "text", flatten=True),
    FieldConfig("ALTCOMPARTID", "Alt_Compartment_Id__c", "Compartment ID", "text"),
    FieldConfig("COMPTYPE", "Compartment_Type__c", "Compartment Type", "text"),
    FieldConfig("TANKEMERGE", "Emergency_Gen__c", "Emergency Generator", "text"),
    FieldConfig("TANKSTATUS", "Status__c", "Tank Status", "text"),
    FieldConfig("TANKCAPACI", "Compartment_Capacity_Gallons__c", "Tank Capacity", "integer"),
    FieldConfig("SUBSTANCED", "Substance__c", "Substance", "text"),
    FieldConfig("SUBSTANCET", "Substance_Type__c", "Substance Type", "text"),
    FieldConfig("TANKMATDES", "Tank__r.Tank_Material__c", "Tank Material", "text", flatten=True),
    FieldConfig("DATEINSTAL", "Tank__r.Date_Installed__c", "Date Installed", "date", flatten=True),
    FieldConfig("DATECLOSE", "Tank__r.Date_Permanently_Closed__c", "Date Permanently Closed", "date", flatten=True),
    FieldConfig("INCOMPLIAN", "Cert_of_Compliance_in_Force__c", "Cert. of Compliance in Force", "text"),
    FieldConfig("PST_FUND", "FR_Type__c", "Fr Type", "text"),
)
