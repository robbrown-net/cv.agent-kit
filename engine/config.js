// Config loading: config/user.json, or an explicit --config path (e.g. config/user.example.json).
const fs = require("fs");
const path = require("path");
const { CvError } = require("./errors");

const DEFAULT_CONFIG = path.join(__dirname, "..", "config", "user.json");

// Returns the config object ({} when no config file is available).
function load(configPath) {
  if (configPath && !fs.existsSync(configPath)) throw new CvError(`config file not found: ${configPath}`);
  const file = configPath || (fs.existsSync(DEFAULT_CONFIG) ? DEFAULT_CONFIG : null);
  if (!file) return {};
  try { return JSON.parse(fs.readFileSync(file, "utf8")); }
  catch (e) { throw new CvError(`could not parse config ${file}: ${e.message}`); }
}

// Page size in twips (A4 or Letter) from config.cv.paper.
function pageSize(config) {
  const cv = (config && config.cv) || {};
  const paper = String(cv.paper || "A4").toUpperCase();
  if (paper !== "A4" && paper !== "LETTER") throw new CvError(`config.cv.paper must be A4 or Letter, got "${cv.paper}"`);
  return paper === "A4" ? { width: 11906, height: 16838 } : { width: 12240, height: 15840 };
}

// Shared layout constants, in twips.
const MARGIN = { top: 580, bottom: 520, left: 840, right: 840 };

module.exports = { load, pageSize, MARGIN, DEFAULT_CONFIG };
