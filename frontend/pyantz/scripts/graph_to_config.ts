/**
 * Turn the graph of the editor into the config which `pyantz` runs.
 *
 * Usage: node scripts/graph_to_config.ts GRAPH.json
 *
 * GRAPH.json is `{ "level": {nodes, edges}, "pipeline": {...} }`, which is what the
 * editor keeps in its store. The config is written to standard output. The python
 * tests use this to check that what the editor exports runs.
 */
import { readFileSync } from "node:fs";
import { graphToConfig } from "../src/model/convert.ts";

const [path, layout] = process.argv.slice(2);
const { level, pipeline } = JSON.parse(readFileSync(path, "utf8"));
process.stdout.write(
  JSON.stringify(
    graphToConfig(level, pipeline, { includeLayout: layout === "--layout" }),
  ),
);
