const fs = require("fs");

// Read the changes from changes.txt
const changes = fs.readFileSync("changes.txt", "utf-8").split("\n");

// Filter Vlocity components
const vlocityComponents = changes.filter((change) =>
  change.startsWith("vlocity/")
);

// Extract unique parent directories of Vlocity components
const modifiedComponents = [
  ...new Set(
    vlocityComponents.map((component) => {
      const pathParts = component.split("/");
      const desiredPart = pathParts.slice(1, pathParts.length - 1).join("/");
      return desiredPart;
    })
  ),
].filter(
  (component) =>
    component.startsWith("DataRaptor") ||
    component.startsWith("OmniScript") ||
    component.startsWith("IntegrationProcedure") ||
    component.startsWith("FlexCard") ||
    component.startsWith("AttributeCategory") ||
    component.startsWith("Product2") ||
    component.startsWith("VlocityCard") ||
    component.startsWith("ContentVersion") ||
    component.startsWith("DocumentTemplate")
);

// Generate YAML content
const yamlContent = `projectPath: vlocity
manifest:
${modifiedComponents.map((component) => `  - ${component}`).join("\n")}
delete: true
activate: true
compileOnBuild: true
maxDepth: -1
continueAfterError: true
defaultMaxParallel: 100
exportPacksMaxSize: 10
useAllRelationships: false
supportHeadersOnly: true
supportForceDeploy: true`;

// Write YAML content to delta-deploy-job.yaml
fs.writeFileSync("delta-deploy-job.yaml", yamlContent);

console.log("Delta deploy job YAML file generated successfully.");
