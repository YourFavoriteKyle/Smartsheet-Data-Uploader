import os
import re
from utils import config
import copy

from smartsheet import Smartsheet

class Generator:

    def __init__(self):
        self.BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
        self.configLoader = config.Config()
        self.appConfig = self.configLoader.getConfigFromFile("app.json")
        self.logger = self.configLoader.getLogger(self.appConfig)
        self.client = Smartsheet(self.appConfig['accessToken'])
        self.mappings = []
        self.sources = []

        cloudMappings = self.getCloudMappings()

        for mappingConfig in cloudMappings:
            sourceTemplate = mappingConfig["sources"]
            mapTemplate = mappingConfig["mapping"]
            reportData = self.getReport(mappingConfig["reportId"], mappingConfig["mappingName"])

            for sourceSheet in reportData.source_sheets:
                # generate sources
                for source in sourceTemplate:
                    newSource = copy.deepcopy(source)
                    sourceId = self.extractProp(newSource["sourceId"])
                    sheetId = self.extractProp(newSource["sheetId"])
                    fileName = self.extractProp(newSource["fileName"])
                    # if no match, use the template values
                    if sourceId == (None, None, None) or fileName == (None, None, None) or sheetId == (None, None, None):
                        pass
                    else:
                        newSource["sourceId"] = "{}{}{}".format(sourceId[0], getattr(sourceSheet, sourceId[1]), sourceId[2])
                        newSource["fileName"] = "{}{}{}".format(fileName[0], getattr(sourceSheet, fileName[1]), fileName[2])
                        newSource["sheetId"] = int("{}{}{}".format(sheetId[0], getattr(sourceSheet, sheetId[1]), sheetId[2]))

                    self.sources.append(newSource)

                # generate mappings
                for mapping in mapTemplate:
                    newMapping = copy.deepcopy(mapping)
                    sheetId = self.extractProp(newMapping["sheetId"])
                    # if no match, use template value
                    if sheetId == (None, None, None):
                        pass
                    else:
                        newMapping["sheetId"] = int("{}{}{}".format(sheetId[0], getattr(sourceSheet, sheetId[1]), sheetId[2]))

                    for index, source in enumerate(newMapping["sources"]):
                        sourceId = self.extractProp(source["sourceId"])
                        # if no match, use template value
                        if sourceId == (None, None, None):
                            pass
                        else:
                            newMapping["sources"][index]["sourceId"] = "{}{}{}".format(sourceId[0], getattr(sourceSheet, sourceId[1]), sourceId[2])

                self.mappings.append(newMapping)

        self.configLoader.validateMappingConfig(self.mappings, self.logger)
        # NOTE: validateSourceConfig is used to validate each source individually, there is no validate all sources right now
        # self.configLoader.validateSourceConfig(self.sources, self.logger, "fileName,hasHeaders")
        self.configLoader.saveConfigToFile(self.sources, "sources.json", self.logger)
        self.configLoader.saveConfigToFile(self.mappings, "mapping.json", self.logger)

    def generateMappings(self):
        self.logger.info("Generating mappings...")
        try:
            self.mappings(self.appConfig, self.configLoader)
        except Exception as e:
            self.logger.error("Error generating mappings: {}".format(e))

    def generateSources(self, fileName: str, sourceName: str):
        self.logger.info("Generating sources...")
        try:
            self.sources(self.appConfig, self.configLoader, fileName, sourceName)
        except Exception as e:
            self.logger.error("Error generating sources: {}".format(e))

    def getCloudMappings(self):
        getAttachments = self.client.Attachments.list_all_attachments(self.appConfig["secretsId"]).data
        matches = []
        for attachment in getAttachments:
            if str(attachment.attachment_type).lower() == "file" and str(attachment.name).lower() == self.appConfig["secretsFileName"]:
                matches.append(attachment)

        attachment = sorted(matches, key=lambda x: x.created_at, reverse=True)[0]
        url = self.client.Attachments.get_attachment(self.appConfig["secretsId"], attachment.id).url
        return self.configLoader.getConfigFromURL(url)

    def getReport(self, reportId, mappingName):
        """
        Easiest if this report is a Summary Report, but not required.
        """
        reportData = {}

        try:
            self.logger.info("Getting report for mapping: {}".format(mappingName))
            reportData = self.client.Reports.get_report(reportId, level=2, include="sourceSheets")
        except Exception as e:
            self.logger.warning("Error getting report for mapping updates. Error: {}".format(e))

        return reportData

    def extractProp(self, prop):
        """
        Takes a string with a section designation for replacement.
        Replacements are designated with double brackets *{{replace me}}*
        This only handles one instance for replacement.

        Returns a tuple of (before, encapsulated, after)
        """
        match = re.search(r"(.*?)\{\{(.*?)\}\}(.*)", prop)
        if match:
            before, encapsulated, after = match.groups()
            return before, encapsulated, after  # Only return the extracted parts, not the {{}}
        else:
            return None, None, None

if __name__ == "__main__":
    generator = Generator()
