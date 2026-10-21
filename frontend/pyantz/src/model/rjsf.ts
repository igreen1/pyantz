import type {
  ErrorTransformer,
  RJSFValidationError,
  ValidatorType,
} from "@rjsf/utils";
import type { JSONSchema7, JSONSchema7TypeName } from "json-schema";
import { isTemplate, propertyKeys, valueAt } from "./templates.ts";

/**
 * Drop the errors about values with `%{name}` placeholders: what they turn into is
 * only known when the pipeline runs.
 */
export const ignoreTemplates =
  (data: unknown): ErrorTransformer =>
  (errors: RJSFValidationError[]) => {
    return errors.filter(
      (error) =>
        error.property === undefined ||
        !isTemplate(valueAt(data, propertyKeys(error.property))),
    );
  };

type UiSchema = Record<string, unknown>;

const isNumeric = (schema: JSONSchema7): boolean => {
  if (schema.type === "integer" || schema.type === "number") return true;
  if (Array.isArray(schema.type)) {
    return schema.type.some((t) => t === "integer" || t === "number");
  }
  return (schema.anyOf ?? []).some(
    (one) => typeof one === "object" && isNumeric(one),
  );
};

/**
 * Show numbers as text, so that a placeholder such as `%{count}` can be typed in:
 * browsers don't let anything but digits into a number input.
 */
export const buildUiSchema = (schema: JSONSchema7): UiSchema => {
  const ui: UiSchema = { "ui:submitButtonOptions": { norender: true } };
  for (const [name, definition] of Object.entries(schema.properties ?? {})) {
    if (typeof definition === "object" && isNumeric(definition)) {
      ui[name] = { "ui:options": { inputType: "text" } };
    }
  }
  return ui;
};

/**
 * Make a validator which does not complain about values with placeholders.
 *
 * The data is filtered as it is given to the validator. A `transformErrors` prop
 * can't do this: the form validates with the one of the render before the change,
 * which would still see the placeholder as it was one keystroke ago.
 */
export const ignoringTemplates = <V extends ValidatorType>(validator: V): V =>
  Object.assign(Object.create(validator as object) as V, {
    validateFormData: (
      formData: unknown,
      schema: Parameters<V["validateFormData"]>[1],
      customValidate: Parameters<V["validateFormData"]>[2],
      transformErrors: Parameters<V["validateFormData"]>[3],
      uiSchema: Parameters<V["validateFormData"]>[4],
    ) =>
      validator.validateFormData(
        formData,
        schema,
        customValidate,
        (errors, ui) =>
          ignoreTemplates(formData)(
            transformErrors?.(errors, ui) ?? errors,
            ui,
          ),
        uiSchema,
      ),
  });

const PRIMITIVES = new Set(["string", "number", "integer", "boolean", "null"]);

/** The types of the alternatives, if they are all plain values. */
const primitiveAlternatives = (
  schema: JSONSchema7,
): JSONSchema7TypeName[] | undefined => {
  const options = [...(schema.anyOf ?? []), ...(schema.oneOf ?? [])];
  if (options.length === 0) return undefined;
  const types: JSONSchema7TypeName[] = [];
  for (const option of options) {
    if (
      typeof option !== "object" ||
      typeof option.type !== "string" ||
      !PRIMITIVES.has(option.type) ||
      option.enum !== undefined
    ) {
      return undefined;
    }
    if (!types.includes(option.type)) types.push(option.type);
  }
  return types;
};

/**
 * Make the schema of a job's parameters one which the form shows well.
 *
 * - The heading and text of the schema as a whole are left out: the inspector says
 *   what the job is.
 * - A parameter which can be one of several plain types (text or a number) is one
 *   field which accepts them all, not a field with a menu for the type. The first
 *   of the types is the one the field is shown as, text if it is one of them.
 */
export const simplifyForForm = (schema: JSONSchema7): JSONSchema7 => {
  const rest = { ...schema };
  delete rest.title;
  delete rest.description;
  const properties = Object.fromEntries(
    Object.entries(schema.properties ?? {}).map(([name, definition]) => {
      if (typeof definition !== "object") return [name, definition];
      const types = primitiveAlternatives(definition);
      if (!types) return [name, definition];
      const field = { ...definition };
      delete field.anyOf;
      delete field.oneOf;
      const ordered = [
        ...types.filter((type) => type === "string"),
        ...types.filter((type) => type !== "string"),
      ];
      return [name, { ...field, type: ordered }];
    }),
  );
  return { ...rest, properties };
};
