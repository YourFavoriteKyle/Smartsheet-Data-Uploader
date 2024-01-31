from utils import config

import os
import csv
from io import StringIO, BytesIO
import urllib, requests
import pandas as pd

theConfig = config.Config()

appConfig = theConfig.getConfigFromFile("app.json")
logger = theConfig.getLogger(appConfig)

class SheetCon:
    def __init__(self, sourceConfig):
        self.config = sourceConfig
        self.data = pd.DataFrame()
        """
		 Example CSV Configuration ( to be set in the settings/sources.json file )
		 {
			"sourceId": "employees",
			"connectorClassName": "SheetCon",
			"fileName": "employees.csv",
			"isStrict": false,
            "cloud": true,
            "sheetId": 0000000
		 }
		 list required fields other than 'sourceId' and 'connectorClassName' from sourceConfig entry
		 'sourceId' and 'connectorClassName' are required for every source, and are already being checked
		"""

        self.getAttachment()
        # self.findSourceMatch("C53562CAT1T", 24)

    def getAttachment(self):
        headers = {"Authorization": "Bearer {}".format(appConfig["accessToken"])}
        attachments = requests.get("{}/sheets/{}/attachments".format(appConfig["apiURL"], self.config["sheetId"]), headers=headers).json()["data"]
        matches = []
        for attachment in attachments:
            if str(attachment["attachmentType"]).lower() == "file" and attachment["name"] == self.config["fileName"]:
                matches.append(attachment)
        matches = sorted(matches, key=lambda x: x["createdAt"], reverse=True)

        if len(matches):
            url = requests.get("{}/sheets/{}/attachments/{}".format(appConfig["apiURL"], self.config["sheetId"], matches[0]["id"]), headers=headers).json()["url"]

            content = requests.get(url)

            if str(attachment["name"]).endswith(".xlsx"):
                self._loadXLSX(BytesIO(content.content))
            if str(attachment["name"]).endswith(".csv"):
                self._loadCSV(BytesIO(content.content))
        else:
            logger.info("No attachment found matching {}.".format(self.config["fileName"]))


    def _loadXLSX(self, data):
        self.data = pd.read_excel(data, index=False)

    def _loadCSV(self, data):
        self.data = pd.read_csv(data, keep_default_na=False)

    def findSourceMatch(self, lookupVal, lookupKey):
        if len(self.data) == 0:
            return []

        match = self.data[self.data.iloc[:, lookupKey] == lookupVal]
        match = match.to_numpy()
        if len(match) > 0:
            return match[0]
        return match

    def findTargetMissing(self, sheetData, lookupMapping):
        """
            lookupMapping = {
                "sourceKey": 0,
                "sheetColumn: "Column Title",
                "sheetColumnId": 0
            }
        """
        sheetDF = []
        for row in sheetData["rows"]:
            for cell in row["cells"]:
                if cell["columnId"] == lookupMapping["sheetColumnId"]:
                    if "displayValue" in cell:
                        sheetDF.append({lookupMapping["sheetColumn"]: cell["displayValue"]})
                    elif "value" in cell:
                        sheetDF.append({lookupMapping["sheetColumn"]: cell["value"]})

        sheetDF = pd.DataFrame.from_records(sheetDF)

        if len(self.data.to_numpy()) == 0:
            self.data = pd.DataFrame(columns=[lookupMapping["sheetColumn"]])

        if len(sheetDF.to_numpy()) == 0:
        	sheetDF = pd.DataFrame(columns=[lookupMapping["sheetColumn"]])

        non_matching = pd.merge(self.data, sheetDF, how='outer', indicator=True, on=lookupMapping["sheetColumn"])
        non_matching = non_matching[(non_matching._merge == 'left_only')]
        non_matching = non_matching.drop("_merge", axis=1)
        non_matching = non_matching.to_numpy()

        return non_matching
