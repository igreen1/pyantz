/**
 * Print the fields of the config models as the editor knows them, as json.
 *
 * Usage: node scripts/dump_model_fields.ts
 *
 * The python tests compare this with the pydantic models, so that a field added on
 * one side only is noticed.
 */
import { MODEL_FIELDS } from "../src/model/types.ts";

process.stdout.write(JSON.stringify(MODEL_FIELDS));
