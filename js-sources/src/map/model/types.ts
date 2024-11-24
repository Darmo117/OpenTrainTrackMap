import { DateInterval } from "./date-interval";

/**
 * This class represents a unit type (e.g. length, speed, etc.).
 */
export class UnitType {
  /**
   * This unit type’s internal label.
   */
  readonly label: string;
  /**
   * This unit type’s localized label.
   */
  readonly localizedName: string;

  readonly #units = new Set<Unit>();

  /**
   * Create a new enum type.
   * @param label The enum’s label.
   * @param localizedName The enum’s localized label.
   */
  constructor(label: string, localizedName: string) {
    this.label = label;
    this.localizedName = localizedName;
  }

  /**
   * This type’s units.
   * @returns A Set of this type’s units.
   */
  get units(): Set<Unit> {
    return new Set(this.#units);
  }

  /**
   * Add a {@link Unit} to this type.
   * @param unit The unit to add.
   * @throws {TypeError} If the type of the given unit is not this type.
   */
  addUnit(unit: Unit): void {
    if (unit.type !== this)
      throw new TypeError(
        `Invalid unit type: expected "${this.label}", got "${unit.type.label}"`,
      );
    this.#units.add(unit);
  }
}

/**
 * This class represents a specific unit of a certain type (e.g. km for length, km/h for speed, etc.).
 */
export class Unit {
  /**
   * This unit’s type.
   */
  readonly type: UnitType;
  /**
   * This unit’s symbol.
   */
  readonly symbol: string;

  /**
   * Create a new unit.
   * @param type The unit’s type.
   * @param symbol The unit’s symbol.
   */
  constructor(type: UnitType, symbol: string) {
    this.type = type;
    this.symbol = symbol;
  }
}

/**
 * Enum values are objects that map each value to its translation in the page’s current language.
 */
export type EnumValues = Record<string, string>;

/**
 * This class represents an enumeration with its label and values.
 */
export class Enum {
  /**
   * This enum’s internal label.
   */
  readonly label: string;
  /**
   * This enum’s localized label.
   */
  readonly localizedName: string;

  readonly #values: EnumValues;

  /**
   * Create a new enum type.
   * @param label The enum’s label.
   * @param localizedName The enum’s localized label.
   * @param values The enum’s values with their translations. Must contain at least one value.
   * @throws {Error} If no values were provided.
   */
  constructor(label: string, localizedName: string, values: EnumValues) {
    this.label = label;
    this.localizedName = localizedName;
    this.#values = { ...values };
    if (this.values.length === 0)
      throw new Error(`Empty enumeration "${label}"`);
  }

  /**
   * An array of this enum’s values, in no particular order.
   */
  get values(): string[] {
    return Object.keys(this.#values);
  }

  /**
   * An array of this enum’s values and their translations.
   * @returns An array of string pairs, each containing a value and its translation in this order.
   */
  get valuesTranslations(): [string, string][] {
    return Object.entries(this.#values);
  }
}

type GeometryType = "Point" | "LineString" | "Polygon" | null;

/**
 * This class represents the type of an object.
 *
 * An `ObjectType` may inherit from another if its `parentType` property is not `null`.
 * In that case, it inherits all properties of this parent type and all of the latter’s parents’.
 */
export class ObjectType {
  /**
   * This type’s internal label.
   */
  readonly label: string;
  /**
   * This type’s localized label.
   */
  readonly localizedName: string;
  /**
   * The type this one inherits from. May be null.
   */
  readonly parentType: ObjectType | null;
  /**
   * Whether this type is deprecated, i.e. whether it should no longer be used.
   */
  readonly isDeprecated: boolean;
  /**
   * Whether this type may be the target of a {@link TemporalProperty}.
   */
  readonly isTemporal: boolean;
  readonly #geometryType: GeometryType | null;
  readonly #properties = new Map<string, ObjectProperty<unknown>>();

  /**
   * Create a new object type.
   * @param label The type’s internal label.
   * @param localizedName The type’s localized label.
   * @param parentType The type’s parent type. May be null.
   * @param geometryType The type of geometry the object may be associated to.
   *  May be null for types that should not be associated to geometries (e.g. relations, operators, etc.).
   * @param temporal Whether this type may be the target of a {@link TemporalProperty}.
   * @param deprecated Whether this type is deprecated, i.e. whether it should no longer be used.
   */
  constructor(
    label: string,
    localizedName: string,
    parentType: ObjectType | null = null,
    geometryType: GeometryType = null,
    temporal = false,
    deprecated = false,
  ) {
    this.label = label;
    this.localizedName = localizedName;
    this.parentType = parentType;
    this.isTemporal = temporal;
    this.isDeprecated = deprecated;
    this.#geometryType = geometryType;
  }

  /**
   * The properties of this object type and its parents’.
   * @returns A stream of this type’s properties.
   */
  get properties(): ObjectProperty<unknown>[] {
    return this.#getProperties().flatMap((entry) => [...entry.values()]);
  }

  #getProperties(): Map<string, ObjectProperty<unknown>>[] {
    const a: Map<string, ObjectProperty<unknown>>[] = [];
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    let type: ObjectType | null = this;
    do {
      a.splice(0, 0, type.#properties); // Insert first
      type = type.parentType;
    } while (type);
    return a;
  }

  /**
   * Get the {@link ObjectProperty} object for the given name.
   * If this object does not possess a property with that name,
   * it is looked for in this object’s parent type hierarchy.
   * @param name The property’s name.
   * @returns {} The {@link ObjectProperty} object for that name
   *  or null if neither this type nor any of its parents
   *  possess a property for that name.
   */
  getProperty(name: string): ObjectProperty<unknown> | null {
    const property = this.#properties.get(name);
    if (!property && this.parentType) return this.parentType.getProperty(name);
    return property ?? null;
  }

  /**
   * Add the given {@link ObjectProperty} to this object type.
   * @param p The property to add.
   * @throws {TypeError} If the `objectType` property of the given property is not this type.
   * @throws {Error} If this object or any of its parents already possesses a property with the exact same `label`.
   */
  addProperty(p: ObjectProperty<unknown>): void {
    if (p.objectType !== this)
      throw new TypeError(
        `Expected type "${this.label}", got "${p.objectType.label}"`,
      );
    if (this.getProperty(p.label))
      throw new Error(
        `Object type ${this.label} already has a property named "${p.label}"`,
      );
    this.#properties.set(p.label, p);
  }

  /**
   * Check whether this object type is the same as the given one or a sub-type.
   * @param other The type to check.
   * @returns True if this type or any of its parent types is the same (according to `===`) as the given one.
   */
  isSameOrSubtypeOf(other: ObjectType): boolean {
    return (
      this === other || (this.parentType?.isSameOrSubtypeOf(other) ?? false)
    );
  }

  /**
   * The type of geometry this object type may be associated to.
   */
  getGeometryType(): GeometryType {
    return this.#geometryType ?? this.parentType?.getGeometryType() ?? null;
  }
}

/**
 * This class represents the definition of a property that can be attached to an {@link ObjectType}.
 *
 * `ObjectProperty`s know which {@link ObjectType} they are attached to.
 */
export abstract class ObjectProperty<T> {
  /**
   * The {@link ObjectType} this property is attached to.
   */
  readonly objectType: ObjectType;
  /**
   * This property’s name prefixed with the object type it is bound to.
   */
  readonly fullName: string;
  /**
   * This property’s label.
   */
  readonly label: string;
  /**
   * This property’s localized label.
   */
  readonly localizedName: string;
  /**
   * Indicates whether this property may have a single value (`true`) or several (`false`).
   */
  readonly isUnique: boolean;
  /**
   * Indicates whether this property is deprecated, i.e. whether it should no longer be used.
   */
  readonly isDeprecated: boolean;

  /**
   * Create an new object property.
   * @param objectType The {@link ObjectType} the property should be attached to.
   * @param label The property’s label.
   * @param localizedName The property’s localized label.
   * @param unique Whether this property may have a single value (`true`) or several (`false`).
   * @param deprecated Whether this property is deprecated, i.e. whether it should no longer be used.
   */
  constructor(
    objectType: ObjectType,
    label: string,
    localizedName: string,
    unique: boolean,
    deprecated: boolean,
  ) {
    this.objectType = objectType;
    this.fullName = `${objectType.label}.${label}`;
    this.label = label;
    this.localizedName = localizedName;
    this.isUnique = unique;
    this.isDeprecated = deprecated;
  }

  /**
   * Check whether the given property value(s) is(are) compatible with this object property.
   *
   * A value is considered compatible if it is bound to a property with the same label,
   * this property’s unicity matches the given property’s unicity, and all values’ types are compatible.
   * @param propertyValue The property value(s) to check.
   * @returns True if the given value(s) is(are) compatible, false otherwise.
   */
  isValueCompatible(
    propertyValue: PropertyValue<unknown, ObjectProperty<unknown>>,
  ): boolean {
    return (
      this.label === propertyValue.propertyType.label &&
      this.isUnique === propertyValue.propertyType.isUnique &&
      ((!propertyValue.propertyType.isUnique &&
        propertyValue.values.every((v) => this.isValueValid(v))) ||
        (propertyValue.propertyType.isUnique &&
          this.isValueValid(propertyValue.value)))
    );
  }

  /**
   * Check whether the given value is valid for this property.
   * @param v The value to check.
   * @returns True if the given value is valid, false otherwise.
   * @apiNotes Implementations should check the actual type of the passed value
   *  as at runtime it may not always match the argument’s declared type.
   */
  abstract isValueValid(v: unknown): boolean;

  /**
   * Create a new {@link PropertyValue} for this property.
   * @param value The initial value.
   * @returns A new {@link PropertyValue}.
   */
  abstract newValue(value: T): PropertyValue<T, ObjectProperty<T>>;
}

/**
 * This class represents a value or set of values bound to an {@link ObjectProperty} definition.
 */
export abstract class PropertyValue<T, OP extends ObjectProperty<T>> {
  /**
   * The {@link ObjectProperty} definition for this value.
   */
  readonly propertyType: OP;
  readonly #values: T[] = [];

  constructor(propertyType: OP, ...values: T[]) {
    this.propertyType = propertyType;
    if (values.length === 0)
      throw new Error(
        `Missing value for property ${this.propertyType.fullName}`,
      );
    if (propertyType.isUnique) {
      if (values.length !== 1)
        throw new Error(
          `Property ${this.propertyType.fullName} expected 1 value, got ${values.length}`,
        );
      this.value = values[0];
    } else this.values = values;
  }

  /**
   * The value bound to this property.
   * @throws {TypeError} If the property is not unique.
   */
  get value(): T {
    this.#ensureUnique();
    return this.#values[0];
  }

  /**
   * Set the value bound to this property.
   * @param value The value to bind.
   * @throws {Error} If the value is invalid for the property.
   * @throws {TypeError} If the property is not unique.
   */
  set value(value: T) {
    this.#ensureUnique();
    this.#ensureValid(value);
    this.#values[0] = value;
  }

  /**
   * The values bound to this property.
   * @throws {TypeError} If the property is unique.
   */
  get values(): T[] {
    this.#ensureNotUnique();
    return [...this.#values];
  }

  /**
   * Set the values bound to this property.
   * @throws {TypeError} If the property is unique.
   */
  set values(values: T[]) {
    this.#ensureNotUnique();
    this.#values.splice(0, this.#values.length, ...values);
  }

  /**
   * Bind a value to the property.
   * @param value The value to bind.
   * @throws {Error} If the value is invalid for the property.
   * @throws {TypeError} If the property is unique.
   */
  addValue(value: T): void {
    this.#ensureNotUnique();
    this.#ensureValid(value);
    this.#values.push(value);
  }

  /**
   * Unbind the given value from the property.
   * Does nothing if the value is not bound to the property.
   * @param value The value to unbind.
   * @throws {Error} If the value is invalid for the property.
   * @throws {TypeError} If the property is unique.
   */
  removeValue(value: T): void {
    this.#ensureNotUnique();
    this.#ensureValid(value);
    const i = this.#values.indexOf(value);
    if (i !== -1) this.#values.splice(i, 1);
  }

  #ensureValid(value: T): void {
    if (!this.propertyType.isValueValid(value))
      throw new Error(
        `Invalid value for property "${this.propertyType.fullName}"`,
      );
  }

  #ensureNotUnique(): void {
    if (this.propertyType.isUnique)
      throw new TypeError(`Property "${this.propertyType.fullName}" is unique`);
  }

  #ensureUnique(): void {
    if (!this.propertyType.isUnique)
      throw new TypeError(
        `Property "${this.propertyType.fullName}" is not unique`,
      );
  }
}

/**
 * This class represents a property that accepts only boolean values.
 */
export class BoolProperty extends ObjectProperty<boolean> {
  isValueValid(v: unknown): boolean {
    return typeof v === "boolean";
  }

  newValue(value: boolean): BoolPropertyValue {
    return new BoolPropertyValue(this, value);
  }
}

/**
 * This class represents a property that accepts only number values.
 */
export abstract class NumberProperty extends ObjectProperty<number> {
  /**
   * If not `null`, the lowest allowed value.
   */
  readonly min: number | null;
  /**
   * If not `null`, the lowest highest value.
   */
  readonly max: number | null;
  /**
   * The type of unit the values represent.
   */
  readonly unitType: UnitType | null;

  /**
   * Create an new number object property.
   * @param objectType The {@link ObjectType} the property should be attached to.
   * @param label The property’s label.
   * @param localizedName The property’s localized label.
   * @param unique Whether this property may have a single value (`true`) or several (`false`).
   * @param deprecated Whether this property is deprecated, i.e. whether it should no longer be used.
   * @param min If specified, the lowest allowed value.
   * @param max If specified, the highest allowed value.
   * @param unitType The type of unit the values represent.
   * @throws {Error} If `min` > `max`.
   */
  constructor(
    objectType: ObjectType,
    label: string,
    localizedName: string,
    unique: boolean,
    deprecated: boolean,
    min?: number,
    max?: number,
    unitType?: UnitType,
  ) {
    super(objectType, label, localizedName, unique, deprecated);
    if (typeof min === "number" && typeof max === "number" && min > max)
      throw new Error("min > max");
    this.min = min ?? null;
    this.max = max ?? null;
    this.unitType = unitType ?? null;
  }

  isValueValid(v: unknown): boolean {
    return (
      typeof v === "number" &&
      (this.min === null || v >= this.min) &&
      (this.max === null || v <= this.max)
    );
  }

  abstract newValue(
    value: number,
    unit?: Unit,
  ): NumberPropertyValue<NumberProperty>;
}

/**
 * This class represents a property that accepts only integer values.
 */
export class IntProperty extends NumberProperty {
  /**
   * Create an new integer object property.
   * @param objectType The {@link ObjectType} the property should be attached to.
   * @param label The property’s label.
   * @param localizedName The property’s localized label.
   * @param unique Whether this property may have a single value (`true`) or several (`false`).
   * @param deprecated Whether this property is deprecated, i.e. whether it should no longer be used.
   * @param min If specified, the lowest allowed value.
   * @param max If specified, the highest allowed value.
   * @param unitType The type of unit the values represent.
   * @throws {Error} If `min` > `max` or any of the two is not an integer.
   */
  constructor(
    objectType: ObjectType,
    label: string,
    localizedName: string,
    unique: boolean,
    deprecated: boolean,
    min?: number,
    max?: number,
    unitType?: UnitType,
  ) {
    super(
      objectType,
      label,
      localizedName,
      unique,
      deprecated,
      min,
      max,
      unitType,
    );
    if (min && !Number.isInteger(min))
      throw new Error("min should be an integer");
    if (max && !Number.isInteger(max))
      throw new Error("max should be an integer");
  }

  isValueValid(v: unknown): boolean {
    return super.isValueValid(v) && Number.isInteger(v);
  }

  newValue(value: number, unit?: Unit): IntPropertyValue {
    return new IntPropertyValue(this, unit, value);
  }
}

/**
 * This class represents a property that accepts only floating point numbers values.
 */
export class FloatProperty extends NumberProperty {
  newValue(value: number, unit?: Unit): FloatPropertyValue {
    return new FloatPropertyValue(this, unit, value);
  }
}

/**
 * This class represents a property that accepts only string values.
 */
export class StringProperty extends ObjectProperty<string> {
  /**
   * Indicates whether this property may accept multiple lines of text.
   */
  readonly multiline: boolean;
  /**
   * Indicates whether this property may have translations.
   */
  readonly translatable: boolean;

  /**
   * Create an new integer object property.
   * @param objectType The {@link ObjectType} the property should be attached to.
   * @param label The property’s label.
   * @param localizedName The property’s localized label.
   * @param unique Whether this property may have a single value (`true`) or several (`false`).
   * @param deprecated Whether this property is deprecated, i.e. whether it should no longer be used.
   * @param multiline Whether this property may accept multiple lines of text.
   * @param translatable Whether this property may have translations.
   */
  constructor(
    objectType: ObjectType,
    label: string,
    localizedName: string,
    unique: boolean,
    deprecated: boolean,
    multiline: boolean,
    translatable: boolean,
  ) {
    super(objectType, label, localizedName, unique, deprecated);
    this.multiline = multiline;
    this.translatable = translatable;
  }

  isValueValid(v: unknown): boolean {
    return (
      typeof v === "string" &&
      (this.multiline || (!v.includes("\n") && !v.includes("\r")))
    );
  }

  newValue(
    value: string,
    translations?: Record<string, string>,
  ): StringPropertyValue {
    return new StringPropertyValue(
      this,
      translations ? [translations] : [],
      value,
    );
  }
}

/**
 * This class represents a property that accepts only {@link DateInterval} values.
 */
export class DateIntervalProperty extends ObjectProperty<DateInterval> {
  isValueValid(v: unknown): boolean {
    return v instanceof DateInterval;
  }

  newValue(value: DateInterval): DateIntervalPropertyValue {
    return new DateIntervalPropertyValue(this, value);
  }
}

/**
 * This class represents a property that accepts only {@link ObjectInstance} values.
 */
export class TypeProperty extends ObjectProperty<ObjectInstance> {
  /**
   * The type of the objects this property can point to.
   */
  readonly targeType: ObjectType;

  /**
   * Create an new integer object property.
   * @param objectType The {@link ObjectType} the property should be attached to.
   * @param label The property’s label.
   * @param localizedName The property’s localized label.
   * @param unique Whether this property may have a single value (`true`) or several (`false`).
   * @param deprecated Whether this property is deprecated, i.e. whether it should no longer be used.
   * @param targetType The type of the objects the property can point to.
   */
  constructor(
    objectType: ObjectType,
    label: string,
    localizedName: string,
    unique: boolean,
    deprecated: boolean,
    targetType: ObjectType,
  ) {
    super(objectType, label, localizedName, unique, deprecated);
    this.targeType = targetType;
  }

  isValueValid(v: unknown): boolean {
    return v instanceof ObjectInstance && v.isInstanceOf(this.targeType);
  }

  newValue(value: ObjectInstance): TypePropertyValue {
    return new TypePropertyValue(this, value);
  }
}

/**
 * This class represents a property that accepts only temporal {@link ObjectInstance} values.
 */
export class TemporalProperty extends TypeProperty {
  /**
   * Whether this property allows date interval overlaps among its target values.
   */
  readonly allowsOverlaps: boolean;

  /**
   * Create an new integer object property.
   * @param objectType The {@link ObjectType} the property should be attached to.
   * @param label The property’s label.
   * @param localizedName The property’s localized label.
   * @param deprecated Whether this property is deprecated, i.e. whether it should no longer be used.
   * @param targetType The type of the objects the property can point to.
   * @param allowsOverlaps Whether the property allows date interval overlaps amongs its target values.
   * @throws {TypeError} If the targetType value is not a temporal object.
   */
  constructor(
    objectType: ObjectType,
    label: string,
    localizedName: string,
    deprecated: boolean,
    targetType: ObjectType,
    allowsOverlaps: boolean,
  ) {
    super(objectType, label, localizedName, false, deprecated, targetType);
    if (!targetType.isTemporal)
      throw new TypeError("Target type is not temporal");
    this.allowsOverlaps = allowsOverlaps;
  }

  isValueValid(v: unknown): boolean {
    // FIXME check overlaps
    return super.isValueValid(v) && (v as ObjectInstance).type.isTemporal;
  }

  newValue(value: ObjectInstance): TemporalObjectPropertyValue {
    return new TemporalObjectPropertyValue(this, value);
  }
}

/**
 * This class represents a property that accepts only {@link Enum} values,
 * i.e. only values from the specified {@link Enum} will be accepted.
 */
export class EnumProperty extends ObjectProperty<string> {
  /**
   * The enumeration this property accepts values from.
   */
  readonly enumType: Enum;

  /**
   * Create an new integer object property.
   * @param objectType The {@link ObjectType} the property should be attached to.
   * @param label The property’s label.
   * @param localizedName The property’s localized label.
   * @param unique Whether this property may have a single value (`true`) or several (`false`).
   * @param deprecated Whether this property is deprecated, i.e. whether it should no longer be used.
   * @param enumType The {@link Enum} whose values this property may only accept.
   */
  constructor(
    objectType: ObjectType,
    label: string,
    localizedName: string,
    unique: boolean,
    deprecated: boolean,
    enumType: Enum,
  ) {
    super(objectType, label, localizedName, unique, deprecated);
    this.enumType = enumType;
  }

  isValueValid(v: unknown): boolean {
    return (
      typeof v === "string" && this.enumType.values.some((value) => value === v)
    );
  }

  newValue(value: string): EnumPropertyValue {
    return new EnumPropertyValue(this, value);
  }
}

/*
 * Instances
 */

/**
 * This class represents an instance of an {@link ObjectType}.
 */
export class ObjectInstance {
  /**
   * This object’s database ID or null if it does not exist in it yet.
   */
  readonly id: number | null;
  #type: ObjectType;
  #existenceInterval: DateInterval | null = null;
  readonly #properties = new Map<
    string,
    PropertyValue<unknown, ObjectProperty<unknown>>
  >();

  /**
   * Create a new object instance of the given type.
   * @param type The object’s type.
   * @param existenceInterval The object’s existence inverval if it is temporal.
   * @param id This object’s database ID. Leave empty for new objects.
   * @throws {Error} If `existenceInterval` is not null and this object is not temporal,
   *  or `existenceInterval` is null and this object is temporal.
   */
  constructor(
    type: ObjectType,
    existenceInterval?: DateInterval | null,
    id?: number,
  ) {
    this.#type = type;
    this.id = id ?? null;
    this.existenceInterval = existenceInterval ?? null;
  }

  /**
   * This object’s type.
   */
  get type(): ObjectType {
    return this.#type;
  }

  /**
   * Set the type of this object. All property values compatible with the new type will be kept,
   * incompatible ones will be discarded.
   *
   * A value is considered compatible if it is bound to a property with the same label,
   * the unicity of the current type’s property matches that of the given type’s equivalent property,
   * and all values’ types are compatible.
   * @param newType The new type.
   * @throws {TypeError} If the new type’s `geometryType` is different from this one’s.
   */
  set type(newType: ObjectType) {
    if (newType !== this.#type) {
      const expectedGeomType = this.#type.getGeometryType();
      const actualGeomType = newType.getGeometryType();
      if (expectedGeomType !== actualGeomType)
        throw new TypeError(
          `Incompatible geometry type, expected "${expectedGeomType}", got "${actualGeomType}"`,
        );

      const toKeep: Record<
        string,
        PropertyValue<unknown, ObjectProperty<unknown>>
      > = {};
      // Store values that are compatible with the new type
      for (const [name, value] of this.#properties) {
        if (newType.getProperty(name)?.isValueCompatible(value))
          toKeep[name] = value;
      }
      this.#properties.clear();
      // Add back the compatible values
      for (const [name, value] of Object.entries(toKeep)) {
        if (value.propertyType.isUnique)
          this.setPropertyValue(name, value.value);
        else for (const v of value.values) this.addValueToProperty(name, v);
      }

      this.#type = newType;
    }
  }

  /**
   * This object’s existence interval if it is temporal, null otherwise.
   */
  get existenceInterval(): DateInterval | null {
    return this.#existenceInterval;
  }

  /**
   * Set this object’s existence interval.
   * @param interval The new interval.
   * @throws {Error} If the value is not null and this object is not temporal,
   *  or the value is null and this object is temporal.
   */
  set existenceInterval(interval: DateInterval | null) {
    if (!this.type.isTemporal && interval)
      throw new Error("Object is not temporal");
    if (this.type.isTemporal && !interval)
      throw new Error("Missing existence interval for temporal object");
    this.#existenceInterval = interval;
  }

  /**
   * Get the value for the given property.
   * @param name The property’s name.
   * @returns The property’s value, or undefined if no value is bound to it.
   * @throws {TypeError} If the property does not exist for this object’s type or it is not unique.
   */
  getPropertyValue(name: string): unknown {
    const { value } = this.#getPropertyOrThrow(name);
    return value?.value;
  }

  /**
   * Set the value of the given property.
   * @param name The property’s name.
   * @param value The property’s value.
   * @throws {TypeError} If the property does not exist for this object’s type or it is not unique.
   * @throws {Error} If the provided value’s type does not match the property’s type.
   */
  setPropertyValue(name: string, value: unknown): void {
    const { property, value: pValue } = this.#getPropertyOrThrow(name);
    if (pValue) pValue.value = value;
    else this.#createPropertyBinding(property, value, name);
  }

  /**
   * Get the values for the given property.
   * @param name The property’s name.
   * @returns The property’s values as an array, or an empty array if no value is bound to it.
   * @throws {TypeError} If the property does not exist for this object’s type or it is unique.
   */
  getPropertyValues(name: string): unknown[] {
    const { value } = this.#getPropertyOrThrow(name);
    return value?.values ?? [];
  }

  /**
   * Add a value to the given property.
   * @param name The property’s name.
   * @param value The value to add to this property.
   * @throws {TypeError} If the property does not exist for this object’s type or is unique.
   */
  addValueToProperty(name: string, value: unknown): void {
    const { property, value: pValue } = this.#getPropertyOrThrow(name);
    if (pValue) pValue.addValue(value);
    else this.#createPropertyBinding(property, value, name);
  }

  /**
   * Remove a value from the given property.
   * If the removed value was the only one, the property is unbound from this object.
   * @param name The property’s name.
   * @param value The value to remove from the property.
   * @throws {TypeError} If the property does not exist for this object’s type or it is unique.
   */
  removeValueFromProperty(name: string, value: unknown): void {
    const { value: pValue } = this.#getPropertyOrThrow(name);
    if (pValue) {
      pValue.removeValue(value);
      if (pValue.values.length === 0) this.#properties.delete(name);
    }
  }

  /**
   * Delete the given property binding.
   * @param name The property’s name.
   * @throws {TypeError} If the property does not exist for this object’s type.
   */
  deleteProperty(name: string): void {
    const { value } = this.#getPropertyOrThrow(name);
    if (value) this.#properties.delete(name);
  }

  /**
   * Fetch the property with the given name in this object or throw an error if it does not exist.
   * @param name The name of the property to fetch.
   * @return An object containing the property definition and its value if any.
   * @throws TypeError If the property is not defined in this object’s type.
   */
  #getPropertyOrThrow(name: string): {
    property: ObjectProperty<unknown>;
    value: PropertyValue<unknown, ObjectProperty<unknown>> | undefined;
  } {
    const property = this.#type.getProperty(name);
    if (!property)
      throw new TypeError(
        `Undefined property "${name}" for object of type "${this.#type.label}"`,
      );
    return { property, value: this.#properties.get(name) };
  }

  #createPropertyBinding(
    property: ObjectProperty<unknown> | NumberProperty,
    value: unknown,
    name: string,
  ) {
    if (property instanceof NumberProperty) {
      if (typeof value !== "number")
        throw new TypeError(`Expected number, got ${typeof value}`);
      this.#properties.set(
        name,
        property.newValue(
          value,
          property.unitType?.units.values().next().value, // Get any unit
        ),
      );
    } else this.#properties.set(name, property.newValue(value));
  }

  /**
   * Get the currently selected unit of the given property.
   * @param name The name of the property to get the unit of.
   * @returns The property’s current unit or null if the property has no bound value.
   * @throws {TypeError} If the property does not exist or it does not have a unit.
   */
  getPropertyUnit(name: string): Unit | null {
    const { property, value } = this.#getPropertyOrThrow(name);
    if (
      !(property instanceof NumberProperty) ||
      (value && !ObjectInstance.#isNumberProperty(value)) ||
      !property.unitType
    )
      throw new TypeError(
        `Property "${property.fullName}" does not have a unit`,
      );
    return value?.unit ?? null;
  }

  /**
   * Set the unit of the given property.
   * @param name The name of the property to set the unit of.
   * @param unit The new unit.
   * @throws {TypeError} If the property does not exist, it does not have a unit, it is not bound yet,
   *  or the new unit’s type is incompatible.
   */
  setPropertyUnit(name: string, unit: Unit): void {
    const { property, value } = this.#getPropertyOrThrow(name);
    if (
      !(property instanceof NumberProperty) ||
      (value && !ObjectInstance.#isNumberProperty(value)) ||
      !property.unitType
    )
      throw new TypeError(
        `Property "${property.fullName}" does not have a unit`,
      );
    if (!value)
      throw new Error(`Property "${property.fullName}" is not bound yet`);
    value.unit = unit;
  }

  // FIXME This function exists because otherwise TS would put a warning on the instanceof check
  static #isNumberProperty(
    value: unknown,
  ): value is NumberPropertyValue<NumberProperty> {
    return value instanceof NumberPropertyValue;
  }

  /**
   * Get the translations of the given string property value.
   * @param name The name of the property to get the translations of.
   * @param index If the property is not unique, the index of the value to get translations of.
   * @returns A map of the value’s translations. The keys are language codes, the values are the associated translations.
   * Null if no value is bound to the property or the index is invalid.
   * @throws {TypeError} If the property does not exist, or it is not translatable.
   */
  getPropertyValueTranslations(
    name: string,
    index?: number,
  ): TranslationMap | null {
    const { property, value } = this.#getPropertyOrThrow(name);
    if (
      !(property instanceof StringProperty) ||
      (value && !(value instanceof StringPropertyValue)) ||
      !property.translatable
    )
      throw new TypeError(
        `Property "${property.fullName}" is not translatable`,
      );
    return value?.translations[index ?? 0] ?? null;
  }

  /**
   * Set the translation of the given string property value for the given language.
   * @param name The name of the property to get the translations of.
   * @param langCode The language code of the translation.
   * @param tr The translated text.
   * @param index If the property is not unique, the index of the value to set the translation of.
   * @throws {TypeError} If the property does not exist, or it is not translatable.
   */
  setPropertyValueTranslation(
    name: string,
    langCode: string,
    tr: string,
    index?: number,
  ): void {
    const { property, value } = this.#getPropertyOrThrow(name);
    if (
      !(property instanceof StringProperty) ||
      (value && !(value instanceof StringPropertyValue)) ||
      !property.translatable
    )
      throw new TypeError(
        `Property "${property.fullName}" is not translatable`,
      );
    value?.setTranslation(langCode, tr, index);
  }

  /**
   * Remove the translation of the given string property value for the given language.
   * @param name The name of the property to get the translations of.
   * @param langCode The language code of the translation.
   * @param index If the property is not unique, the index of the value to set remove the translation from.
   * @throws {TypeError} If the property does not exist, or it is not translatable.
   */
  removePropertyValueTranslation(
    name: string,
    langCode: string,
    index?: number,
  ): void {
    const { property, value } = this.#getPropertyOrThrow(name);
    if (
      !(property instanceof StringProperty) ||
      (value && !(value instanceof StringPropertyValue)) ||
      !property.translatable
    )
      throw new TypeError(
        `Property "${property.fullName}" is not translatable`,
      );
    value?.removeTranslation(langCode, index);
  }

  /**
   * Check whether this object is an instance of the given {@link ObjectType}.
   * @param t The type to check.
   * @returns True if this object has the given type in its type hierarchy, false otherwise.
   * @see ObjectType.isSameOrSubtypeOf
   */
  isInstanceOf(t: ObjectType): boolean {
    return this.#type.isSameOrSubtypeOf(t);
  }
}

/**
 * This class represents the single boolean value bound to an {@link BoolProperty} definition
 * with a `isUnique` field set to `true`.
 */
export class BoolPropertyValue extends PropertyValue<boolean, BoolProperty> {}

/**
 * This class represents the number value(s) bound to a {@link NumberProperty} definition.
 */
export abstract class NumberPropertyValue<
  OP extends NumberProperty,
> extends PropertyValue<number, OP> {
  #unit: Unit | null = null;

  /**
   * Create a new number property value.
   * @param propertyType The property to bind the value to.
   * @param unit Optional. The unit to attach to each value.
   * @param values The values to bind to the property.
   * @throws {TypeError} If the value is invalid for the property
   *  or the unit’s type differs from the one defined by the property.
   */
  constructor(propertyType: OP, unit?: Unit, ...values: number[]) {
    super(propertyType, ...values);
    if (propertyType.unitType && !unit)
      throw new Error(`Missing unit for property ${propertyType.fullName}`);
    if (unit) this.unit = unit;
  }

  /**
   * The unit attached to this value. May be null.
   */
  get unit(): Unit | null {
    return this.#unit;
  }

  /**
   * Set the unit attached to this value.
   * @throws {TypeError} If the unit’s type differs from the one defined by the property.
   * @throws {Error} If the unit is null but one is required.
   */
  set unit(unit: Unit) {
    const expectedType = this.propertyType.unitType;
    if (!expectedType)
      throw new TypeError(
        `Unexpected unit for property "${this.propertyType.fullName}"`,
      );
    const actualType = unit.type;
    if (expectedType !== actualType)
      throw new TypeError(
        `Invalid unit type for property "${this.propertyType.fullName}": expected "${expectedType.label}", got "${actualType}"`,
      );
    this.#unit = unit;
  }
}

/**
 * This class represents the int value(s) bound to an {@link IntProperty} definition.
 */
export class IntPropertyValue extends NumberPropertyValue<IntProperty> {}

/**
 * This class represents the float value(s) bound to a {@link FloatProperty} definition.
 */
export class FloatPropertyValue extends NumberPropertyValue<FloatProperty> {}

/**
 * A translation map associates language codes with a translation.
 */
export type TranslationMap = Map<string, string>;

/**
 * This class represents the string value(s) bound to a {@link StringProperty} definition.
 */
export class StringPropertyValue extends PropertyValue<string, StringProperty> {
  readonly #translations: TranslationMap[];

  /**
   * Create a new string property value.
   * @param values The values to bind to the property.
   * @param propertyType The property to bind the value to.
   * @param translations Optional. The existing translations for this value.
   * @throws {Error} If translations are provided but the property is not translatable.
   */
  constructor(
    propertyType: StringProperty,
    translations?: Record<string, string>[],
    ...values: string[]
  ) {
    super(propertyType, ...values);
    if (translations) this.#ensureTranslatable();
    if (translations && translations.length > values.length)
      throw new Error("Too many translations");
    this.#translations =
      translations?.map((tr) => new Map(Object.entries(tr))) ?? [];
  }

  /**
   * The translations for each value of this property.
   * @returns A new array containing a {@link TranslationMap} for each value,
   * in the same order as {@link PropertyValue#values}.
   */
  get translations(): TranslationMap[] {
    return structuredClone(this.#translations);
  }

  /**
   * Set the translation for the given language code.
   * @param langCode The language code.
   * @param tr The translation for that language.
   * @param index If the property is not unique, the index of the value to set the translation of.
   * @throws {Error} If the property is not translatable or the index is invalid.
   */
  setTranslation(langCode: string, tr: string, index?: number): void {
    this.#ensureTranslatable();
    this.#translations[index ?? 0].set(langCode, tr);
  }

  /**
   * Remove the translation for the given language code.
   * @param langCode The language code.
   * @param index If the property is not unique, the index of the value to remove the translation from.
   * @throws {Error} If the property is not translatable.
   */
  removeTranslation(langCode: string, index?: number): void {
    this.#ensureTranslatable();
    this.#translations[index ?? 0].delete(langCode);
  }

  #ensureTranslatable() {
    if (!this.propertyType.translatable)
      throw new Error(
        `Property "${this.propertyType.fullName}" is not translatable`,
      );
  }
}

/**
 * This class represents the {@link DateInterval} value(s) bound to a {@link DateIntervalProperty} definition.
 */
export class DateIntervalPropertyValue extends PropertyValue<
  DateInterval,
  DateIntervalProperty
> {}

/**
 * This class represents the {@link ObjectInstance} value(s) bound to a {@link TypeProperty} definition.
 */
export class TypePropertyValue<
  OP extends TypeProperty = TypeProperty,
> extends PropertyValue<ObjectInstance, OP> {}

/**
 * This class represents the single enum value(s) bound to an {@link EnumProperty} definition.
 */
export class EnumPropertyValue extends PropertyValue<string, EnumProperty> {}

/**
 * This class represents the temporal objects bound to a {@link TemporalProperty} definition.
 */
export class TemporalObjectPropertyValue extends TypePropertyValue<TemporalProperty> {
  /**
   * Set the values bound to this property.
   * @throws {TypeError} If the property is unique.
   */
  set values(values: ObjectInstance[]) {
    values.forEach((v) => {
      this.addValue(v);
    });
  }

  addValue(value: ObjectInstance): void {
    this.#checkOverlaps(value);
    super.addValue(value);
  }

  #checkOverlaps(value: ObjectInstance): void {
    if (
      !this.propertyType.allowsOverlaps &&
      this.values.some(
        (o) =>
          !!value.existenceInterval &&
          !!o.existenceInterval &&
          value.existenceInterval.overlaps(o.existenceInterval),
      )
    )
      throw new Error("Object’s existence interval overlaps another one’s");
  }
}
