// Runtime configuration, replaced when the container starts.
//
// Vite bakes `import.meta.env` values into the bundle at build time, which
// would mean rebuilding the image to point it at a different API. This file is
// read at load instead, so the deployed container can be told where the API is
// through an ordinary environment variable. An empty object means "fall back
// to the build-time value", which is what local development uses.
window.__SCICONNECT__ = {};
