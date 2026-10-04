// Error type carrying an optional 1-based source line number.
class CvError extends Error {
  constructor(msg, line) {
    super(msg);
    this.name = "CvError";
    this.line = line || null;
  }
}
module.exports = { CvError };
