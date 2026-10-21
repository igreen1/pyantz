/** Configs may contain `%{name}` placeholders, which are filled in when they run. */

const TEMPLATE = /%\{[^}]+\}/;

export const isTemplate = (value: unknown): boolean =>
  typeof value === "string" && TEMPLATE.test(value);

/** Get the value at a json pointer-like list of keys, or undefined. */
export const valueAt = (data: unknown, keys: readonly string[]): unknown => {
  let current = data;
  for (const key of keys) {
    if (typeof current !== "object" || current === null) return undefined;
    current = (current as Record<string, unknown>)[key];
  }
  return current;
};

/** Split `/a/0/b` (ajv) into keys. */
export const pointerKeys = (pointer: string): string[] =>
  pointer === ""
    ? []
    : pointer
        .slice(1)
        .split("/")
        .map((key) => key.replaceAll("~1", "/").replaceAll("~0", "~"));

/** Split `.a[0].b` or `.a['x y']` (react-jsonschema-form) into keys. */
export const propertyKeys = (property: string): string[] => {
  const keys: string[] = [];
  const part = /\.([^.[\]]+)|\[(\d+)\]|\['([^']*)'\]/g;
  for (const match of property.matchAll(part)) {
    keys.push(match[1] ?? match[2] ?? match[3]);
  }
  return keys;
};
