import * as stream from "../../streams";
import * as di from "./date-interval"

/*
 * Meta-model
 */

/**
 * Name of the parent type of all temporal state types.
 */
export const TEMPORAL_STATE_TYPE_NAME: string = "temporal_state";

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
  readonly #units: Set<Unit> = new Set();

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
   * @returns An unordered stream of this type’s units.
   */
  get units(): stream.Stream<Unit> {
    return stream.stream(this.#units);
  }

  /**
   * Add a {@link Unit} to this type.
   * @param unit The unit to add.
   * @throws {TypeError} If the type of the given unit is not this type.
   */
  addUnit(unit: Unit): void {
    if (unit.type !== this) {
      throw new TypeError(`Invalid unit type: expected "${this.label}", got "${unit.type.label}"`);
    }
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
export type EnumValues = {
  [value: string]: string;
};

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
    this.#values = {...values};
    if (this.values.count() === 0) {
      throw new Error(`Empty enumeration "${label}"`);
    }
  }

  /**
   * A stream of this enum’s values.
   */
  get values(): stream.Stream<string> {
    return stream.streamOfObject(this.#values).map(([key, _]) => key);
  }

  /**
   * A stream of this enum’s values and their translations.
   * @returns A stream of string pairs, each containing a value and its translation in this order.
   */
  get valuesTranslations(): stream.Stream<[string, string]> {
    return stream.streamOfObject(this.#values);
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
  readonly #geometryType: GeometryType | null;
  readonly #properties: { [name: string]: ObjectProperty<any> } = {};

  /**
   * Create a new object type.
   * @param label The type’s internal label.
   * @param localizedName The type’s localized label.
   * @param parentType The type’s parent type. May be null.
   * @param geometryType The type of geometry the object may be associated to.
   *  May be null for types that should not be associated to geometries (e.g. relations, operators, etc.).
   */
  constructor(label: string, localizedName: string, parentType: ObjectType = null, geometryType: GeometryType = null) {
    this.label = label;
    this.localizedName = localizedName;
    this.parentType = parentType;
    this.#geometryType = geometryType;
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
  getProperty(name: string): ObjectProperty<any> | null {
    const property = this.#properties[name];
    if (!property && this.parentType) {
      return this.parentType.getProperty(name);
    }
    return property ?? null;
  }

  /**
   * Add the given {@link ObjectProperty} to this object type.
   * @param p The property to add.
   * @throws {TypeError} If the `objectType` property of the given property is not this type.
   * @throws {Error} If this object or any of its parents already possesses a property with the exact same `label`.
   */
  addProperty(p: ObjectProperty<any>): void {
    if (p.objectType != this) {
      throw new TypeError(`Expected type "${this.label}", got "${p.objectType.label}"`);
    }
    if (this.getProperty(p.label)) {
      throw new Error(`Object type ${this.label} already has a property named "${p.label}"`);
    }
    this.#properties[p.label] = p;
  }

  /**
   * Check whether this object type is the same as the given one or a sub-type.
   * @param other The type to check.
   * @returns True if this type or any of its parent types is the same (according to `===`) as the given one.
   */
  isSameOrSubtypeOf(other: ObjectType): boolean {
    return this === other || (this.parentType?.isSameOrSubtypeOf(other) ?? false);
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
      deprecated: boolean
  ) {
    this.objectType = objectType;
    this.fullName = `${objectType.label}.${label}`;
    this.label = label;
    this.localizedName = localizedName;
    this.isUnique = unique;
    this.isDeprecated = deprecated;
  }

  /**
   * Check whether the given value is valid for this property.
   * @param v The value to check.
   * @returns True if the given value is valid, false otherwise.
   * @apiNotes Implementations should check the actual type of the passed value
   *  as at runtime it may not always match the argument’s declared type.
   */
  abstract isValueValid(v: T): boolean;

  /**
   * Check whether the given property value is compatible with this object property.
   *
   * A value is considered compatible if it is bound to a property with the same label,
   * and this property is unique and the value is a {@link SingleObjectPropertyValue} and it is valid,
   * or this property is not unique and the value is a {@link MultipleObjectPropertyValue} and all are valid.
   * @param propertyValue The value to check.
   * @returns True if the given value is compatible, false otherwise.
   */
  isValueCompatible(propertyValue: ObjectPropertyValue<any, any>): boolean {
    return this.label === propertyValue.propertyType.label
        && ((this.isUnique && propertyValue instanceof SingleObjectPropertyValue
                && this.isValueValid(propertyValue.value))
            || (!this.isUnique && propertyValue instanceof MultipleObjectPropertyValue
                && propertyValue.getValues().allMatch(v => this.isValueValid(v)))
        );
  }

  /**
   * Create a new {@link ObjectPropertyValue} for this property.
   * @param value The initial value.
   * @returns {} A {@link SingleObjectPropertyValue} if this property is unique,
   *  a {@link MultipleObjectPropertyValue} otherwise.
   */
  abstract newValue(value: T): SingleObjectPropertyValue<T, ObjectProperty<T>>
      | MultipleObjectPropertyValue<T, ObjectProperty<T>>;
}

/**
 * This class represents a property that accepts only boolean values.
 */
export class BoolProperty extends ObjectProperty<boolean> {
  isValueValid(v: boolean): boolean {
    return typeof v === "boolean";
  }

  newValue(value: boolean): SingleObjectPropertyValue<boolean, BoolProperty>
      | MultipleObjectPropertyValue<boolean, BoolProperty> {
    return this.isUnique
        ? new SingleObjectPropertyValue(value, this)
        : new MultipleObjectPropertyValue(value, this);
  }
}

/**
 * This class represents a property that accepts only integer values.
 */
export class IntProperty extends ObjectProperty<number> {
  /**
   * If not `null`, the lowest allowed value.
   */
  readonly min: number | null;
  /**
   * If not `null`, the lowest highest value.
   */
  readonly max: number | null
  /**
   * The type of unit the values represent.
   */
  readonly unitType: UnitType | null;

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
      min: number = null,
      max: number = null,
      unitType: UnitType = null
  ) {
    super(objectType, label, localizedName, unique, deprecated);
    if (typeof min === "number" && typeof max === "number" && min > max) {
      throw new Error("min > max");
    }
    if (typeof min === "number" && !Number.isInteger(min)) {
      throw new Error("min should be an integer");
    }
    if (typeof max === "number" && !Number.isInteger(max)) {
      throw new Error("max should be an integer");
    }
    this.min = min;
    this.max = max;
    this.unitType = unitType;
  }

  isValueValid(v: number): boolean {
    return Number.isInteger(v)
        && (this.min === null || v >= this.min)
        && (this.max === null || v <= this.max);
  }

  newValue(value: number, unit?: Unit): IntSingleObjectPropertyValue | IntMultipleObjectPropertyValue {
    return this.isUnique
        ? new IntSingleObjectPropertyValue(value, this, unit)
        : new IntMultipleObjectPropertyValue(value, this, unit);
  }
}

/**
 * This class represents a property that accepts only floating point numbers values.
 */
export class FloatProperty extends ObjectProperty<number> {
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
   * Create an new integer object property.
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
      min: number = null,
      max: number = null,
      unitType: UnitType = null
  ) {
    super(objectType, label, localizedName, unique, deprecated);
    if (min > max) {
      throw new Error("min > max");
    }
    this.min = min;
    this.max = max;
    this.unitType = unitType;
  }

  isValueValid(v: number): boolean {
    return typeof v === "number"
        && (this.min === null || v >= this.min)
        && (this.max === null || v <= this.max);
  }

  newValue(value: number, unit?: Unit): FloatSingleObjectPropertyValue | FloatMultipleObjectPropertyValue {
    return this.isUnique
        ? new FloatSingleObjectPropertyValue(value, this, unit)
        : new FloatMultipleObjectPropertyValue(value, this, unit);
  }
}

/**
 * This class represents a property that accepts only string values.
 */
export class StringProperty extends ObjectProperty<string> {
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
   * @param translatable Whether this property may have translations.
   */
  constructor(
      objectType: ObjectType,
      label: string,
      localizedName: string,
      unique: boolean,
      deprecated: boolean,
      translatable: boolean
  ) {
    super(objectType, label, localizedName, unique, deprecated);
    this.translatable = translatable;
  }

  isValueValid(v: string): boolean {
    return typeof v === "string";
  }

  newValue(value: string, translations?: { [langCode: string]: string }): StringSingleObjectPropertyValue
      | StringMultipleObjectPropertyValue {
    return this.isUnique
        ? new StringSingleObjectPropertyValue(value, this, translations)
        : new StringMultipleObjectPropertyValue(value, this, translations);
  }
}

/**
 * This class represents a property that accepts only {@link di.DateInterval} values.
 */
export class DateIntervalProperty extends ObjectProperty<di.DateInterval> {
  isValueValid(v: di.DateInterval): boolean {
    return v instanceof di.DateInterval;
  }

  newValue(value: di.DateInterval): SingleObjectPropertyValue<di.DateInterval, DateIntervalProperty>
      | MultipleObjectPropertyValue<di.DateInterval, DateIntervalProperty> {
    return this.isUnique
        ? new SingleObjectPropertyValue(value, this)
        : new MultipleObjectPropertyValue(value, this);
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
      targetType: ObjectType
  ) {
    super(objectType, label, localizedName, unique, deprecated);
    this.targeType = targetType;
  }

  isValueValid(v: ObjectInstance): boolean {
    return v instanceof ObjectInstance && v.isInstanceOf(this.targeType);
  }

  newValue(value: ObjectInstance): SingleObjectPropertyValue<ObjectInstance, TypeProperty>
      | MultipleObjectPropertyValue<ObjectInstance, TypeProperty> {
    return this.isUnique
        ? new SingleObjectPropertyValue(value, this)
        : new MultipleObjectPropertyValue(value, this);
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
      enumType: Enum
  ) {
    super(objectType, label, localizedName, unique, deprecated);
    this.enumType = enumType;
  }

  isValueValid(v: string): boolean {
    return typeof v === "string" && this.enumType.values.anyMatch(value => value === v);
  }

  newValue(value: string): SingleObjectPropertyValue<string, EnumProperty>
      | MultipleObjectPropertyValue<string, EnumProperty> {
    return this.isUnique
        ? new SingleObjectPropertyValue(value, this)
        : new MultipleObjectPropertyValue(value, this);
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
  readonly #uniqueProperties: { [name: string]: SingleObjectPropertyValue<any, any> } = {};
  readonly #multiProperties: { [name: string]: MultipleObjectPropertyValue<any, any> } = {};

  /**
   * Create a new object instance of the given type.
   * @param type The object’s type.
   * @param id This object’s database ID. Leave empty for new objects.
   */
  constructor(type: ObjectType, id?: number) {
    this.#type = type;
    this.id = id;
  }

  /**
   * This object’s type.
   */
  get type(): ObjectType {
    return this.#type;
  }

  /**
   * Set the type of this object. All incompatible property values will be discarded,
   * only the ones compatible with the new type will be kept.
   * @param newType The new type.
   * @throws {TypeError} If the new type’s `geometryType` is different from this one’s.
   * @see ObjectProperty.isValueCompatible
   */
  setType(newType: ObjectType): void {
    if (newType !== this.#type) {
      const expectedGeomType = this.#type.getGeometryType();
      const actualGeomType = newType.getGeometryType();
      if (expectedGeomType !== actualGeomType) {
        throw new TypeError(`Incompatible geometry type, expected "${expectedGeomType}", got "${actualGeomType}"`);
      }

      // Delete properties that are not compatible with the new type
      for (const [name, value] of Object.entries(this.#uniqueProperties)) {
        if (!newType.getProperty(name)?.isValueCompatible(value)) {
          delete this.#uniqueProperties[name];
        }
      }
      for (const [name, value] of Object.entries(this.#multiProperties)) {
        if (!newType.getProperty(name)?.isValueCompatible(value)) {
          delete this.#multiProperties[name];
        }
      }

      this.#type = newType;
    }
  }

  /**
   * Get the value for the given property.
   * @param name The property’s name.
   * @returns The property’s value, or null if it has never been set or has been removed but not set again afterwards.
   * @throws {TypeError} If the property does not exist for this object’s type or is not unique.
   */
  getPropertyValue<T>(name: string): T | null {
    this.#getUniquePropertyOrThrow(name);
    return this.#uniqueProperties[name]?.value ?? null;
  }

  /**
   * Set the value of the given property.
   * @param name The property’s name.
   * @param value The property’s value.
   * @throws {TypeError} If the property does not exist for this object’s type or is not unique.
   */
  setPropertyValue<T>(name: string, value: T): void {
    const property = this.#getUniquePropertyOrThrow(name);
    const pValue = this.#uniqueProperties[name];
    if (pValue) {
      pValue.setValue(value);
    } else {
      let propValue: SingleObjectPropertyValue<T, ObjectProperty<any>>;
      if ((property instanceof IntProperty || property instanceof FloatProperty) && property.unitType) {
        propValue = property.newValue(value as number, property.unitType.units.findFirst().get()) as any;
      } else {
        propValue = property.newValue(value) as any;
      }
      this.#uniqueProperties[name] = propValue;
    }
  }

  /**
   * Remove the value for the given property.
   * @param name The property’s name.
   * @throws {TypeError} If the property does not exist for this object’s type or is not unique.
   */
  removePropertyValue(name: string): void {
    this.#getUniquePropertyOrThrow(name);
    if (this.#uniqueProperties[name]) {
      delete this.#uniqueProperties[name];
    }
  }

  #getUniquePropertyOrThrow(name: string): ObjectProperty<any> {
    const property = this.#type.getProperty(name);
    if (!property) {
      throw new TypeError(`Invalid property "${name}" for object of type "${this.#type.label}"`);
    }
    if (!property.isUnique) {
      throw new TypeError(`Property "${name}" is not unique`);
    }
    return property;
  }

  /**
   * Get the values for the given property.
   * @param name The property’s name.
   * @returns The property’s values as a stream, or an empty stream if it has never been set
   *  or has been removed but not set again afterwards.
   * @throws {TypeError} If the property does not exist for this object’s type or is unique.
   */
  getPropertyValues<T>(name: string): stream.Stream<T> {
    this.#getMultiplePropertyOrThrow(name);
    return this.#multiProperties[name]?.getValues() ?? stream.emptyStream();
  }

  /**
   * Add a value to the given property.
   * @param name The property’s name.
   * @param value The value to add to this property.
   * @throws {TypeError} If the property does not exist for this object’s type or is unique.
   */
  addValueToProperty<T>(name: string, value: T): void {
    const property = this.#getMultiplePropertyOrThrow(name);
    const pValue = this.#multiProperties[name];
    if (pValue) {
      pValue.addValue(value);
    } else {
      let propValue: MultipleObjectPropertyValue<T, ObjectProperty<any>>;
      if ((property instanceof IntProperty || property instanceof FloatProperty) && property.unitType) {
        propValue = property.newValue(value as number, property.unitType.units.findFirst().get()) as any;
      } else {
        propValue = property.newValue(value) as any;
      }
      this.#multiProperties[name] = propValue;
    }
  }

  /**
   * Remove a value from the given property.
   * If the removed value was the only one, the property is removed from this object.
   * @param name The property’s name.
   * @param value The value to remove from the property.
   * @throws {TypeError} If the property does not exist for this object’s type or is unique.
   */
  removeValueFromProperty<T>(name: string, value: T): void {
    this.#getMultiplePropertyOrThrow(name);
    const p = this.#multiProperties[name];
    if (p) {
      p.removeValue(value);
      if (p.getValues().count() === 0) {
        delete this.#multiProperties[name];
      }
    }
  }

  #getMultiplePropertyOrThrow(name: string): ObjectProperty<any> {
    const property = this.#type.getProperty(name);
    if (!property) {
      throw new TypeError(`Invalid property "${name}" for object of type "${this.#type.label}"`);
    }
    if (property.isUnique) {
      throw new TypeError(`Property "${name}" is unique`);
    }
    return property;
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
 * This class represents a value bound to a {@link ObjectProperty} definition.
 */
export abstract class ObjectPropertyValue<T, OP extends ObjectProperty<T>> {
  /**
   * The {@link ObjectProperty} definition for this value.
   */
  readonly propertyType: OP;

  protected constructor(propertyType: OP) {
    this.propertyType = propertyType;
  }
}

/**
 * This class represents the single value bound to an {@link ObjectProperty} definition
 * with a `isUnique` field set to `true`.
 */
export class SingleObjectPropertyValue<T, OP extends ObjectProperty<T>> extends ObjectPropertyValue<T, OP> {
  #value: T;

  /**
   * Create a new property value.
   * @param value The value to bind to the property.
   * @param propertyType The property to bind the value to.
   * @throws {TypeError} If the value is invalid for the property.
   */
  constructor(value: T, propertyType: OP) {
    super(propertyType);
    this.setValue(value);
  }

  /**
   * The property’s value.
   */
  get value(): T {
    return this.#value;
  }

  /**
   * Set the property’s value.
   * @param value The new value.
   * @throws {TypeError} If the value is invalid for the property.
   */
  setValue(value: T): void {
    if (!this.propertyType.isValueValid(value)) {
      throw new TypeError(`Invalid value for property "${this.propertyType.fullName}"`);
    }
    this.#value = value;
  }
}

/**
 * This class represents the single int value bound to an {@link IntProperty} definition
 * with a `isUnique` field set to `true`.
 */
export class IntSingleObjectPropertyValue extends SingleObjectPropertyValue<number, IntProperty> {
  #unit: Unit | null;

  /**
   * Create a new int property value.
   * @param value The value to bind to the property.
   * @param propertyType The property to bind the value to.
   * @param unit Optional. The unit to attach to this value.
   * @throws {TypeError} If the value is invalid for the property
   *  or the unit’s type differs from the one defined by the property.
   */
  constructor(value: number, propertyType: IntProperty, unit?: Unit) {
    super(value, propertyType);
    this.unit = unit;
  }

  /**
   * The unit attached to this value. May be null.
   */
  get unit(): Unit | null {
    return this.#unit;
  }

  /**
   * Set the unit attached to this value. May be null.
   * @throws {TypeError} If the unit’s type differs from the one defined by the property.
   * @throws {Error} If the unit is null or undefined.
   */
  set unit(unit: Unit) {
    const expectedType = this.propertyType.unitType;
    if (!unit && !expectedType) {
      return;
    }
    if (!unit && expectedType) {
      throw new Error(`Undefined unit`);
    }
    if (unit && !expectedType) {
      throw new TypeError(`Unexpected unit for property "${this.propertyType.fullName}"`);
    }
    const actualType = unit.type;
    if (expectedType !== actualType) {
      throw new TypeError(`Invalid unit type for property "${this.propertyType.fullName}": expected "${expectedType?.label}", got "${actualType}"`);
    }
    this.#unit = unit;
  }
}

/**
 * This class represents the single float value bound to an {@link FloatProperty} definition
 * with a `isUnique` field set to `true`.
 */
export class FloatSingleObjectPropertyValue extends SingleObjectPropertyValue<number, FloatProperty> {
  #unit: Unit | null;

  /**
   * Create a new float property value.
   * @param value The value to bind to the property.
   * @param propertyType The property to bind the value to.
   * @param unit Optional. The unit to attach to this value.
   * @throws {TypeError} If the value is invalid for the property
   *  or the unit’s type differs from the one defined by the property.
   */
  constructor(value: number, propertyType: FloatProperty, unit?: Unit) {
    super(value, propertyType);
    this.unit = unit;
  }

  /**
   * The unit attached to this value. May be null.
   */
  get unit(): Unit | null {
    return this.#unit;
  }

  /**
   * Set the unit attached to this value. May be null.
   * @throws {TypeError} If the unit’s type differs from the one defined by the property.
   * @throws {Error} If the unit is null or undefined.
   */
  set unit(unit: Unit) {
    const expectedType = this.propertyType.unitType;
    if (!unit && !expectedType) {
      return;
    }
    if (!unit && expectedType) {
      throw new Error(`Undefined unit`);
    }
    if (unit && !expectedType) {
      throw new TypeError(`Unexpected unit for property "${this.propertyType.fullName}"`);
    }
    const actualType = unit.type;
    if (expectedType !== actualType) {
      throw new TypeError(`Invalid unit type for property "${this.propertyType.fullName}": expected "${expectedType?.label}", got "${actualType}"`);
    }
    this.#unit = unit;
  }
}

/**
 * This class represents the single string value bound to an {@link StringProperty} definition
 * with a `isUnique` field set to `true`.
 */
export class StringSingleObjectPropertyValue extends SingleObjectPropertyValue<string, StringProperty> {
  readonly #translations: { [langCode: string]: string };

  /**
   * Create a new string property value.
   * @param value The value to bind to the property.
   * @param propertyType The property to bind the value to.
   * @param translations Optional. The existing translations for this value.
   * @throws {Error} If translations are provided but the property is not translatable.
   */
  constructor(value: string, propertyType: StringProperty, translations?: { [langCode: string]: string }) {
    super(value, propertyType);
    if (translations) {
      this.#ensureTranslatable();
    }
    this.#translations = {...translations};
  }

  /**
   * The translations for this string value.
   * @returns A stream of string pairs, each containing the language code and the text for that language in that order.
   */
  get translations(): stream.Stream<[string, string]> {
    return stream.streamOfObject(this.#translations);
  }

  /**
   * Set the translation for the given language code.
   * @param langCode The language code.
   * @param tr The translation for that language.
   * @throws {Error} If the property is not translatable.
   */
  setTranslation(langCode: string, tr: string): void {
    this.#ensureTranslatable();
    this.#translations[langCode] = tr;
  }

  /**
   * Remove the translation for the given language code.
   * @param langCode The language code.
   * @throws {Error} If the property is not translatable.
   */
  removeTranslation(langCode: string): void {
    this.#ensureTranslatable();
    delete this.#translations[langCode];
  }

  #ensureTranslatable() {
    if (!this.propertyType.translatable) {
      throw new Error(`Property "${this.propertyType.fullName}" is not translatable`);
    }
  }
}

/**
 * This class represents the values bound to {@link ObjectProperty} definition
 * with a `isUnique` field set to `false`.
 */
export class MultipleObjectPropertyValue<T, OP extends ObjectProperty<T>> extends ObjectPropertyValue<T, OP> {
  readonly #value: T[] = [];

  /**
   * Create a new multiple property value.
   * @param firstValue The first value to bind to the property.
   * @param propertyType The property to bind the value to.
   * @throws {TypeError} If the value is invalid for the property.
   */
  constructor(firstValue: T, propertyType: OP) {
    super(propertyType);
    this.addValue(firstValue)
  }

  /**
   * The values of the property.
   * @returns A stream of all values bound to the property.
   */
  getValues(): stream.Stream<T> {
    return stream.stream(this.#value);
  }

  /**
   * Bind a value to the property.
   * @param value The value to bind.
   * @throws {TypeError} If the value is invalid for the property.
   */
  addValue(value: T): void {
    if (!this.propertyType.isValueValid(value)) {
      throw new Error(`Invalid value for property "${this.propertyType.objectType.label}.${this.propertyType.label}"`);
    }
    this.#value.push(value);
  }

  /**
   * Unbind the given value from the property.
   * Does nothing if the value is not bound to the property.
   * @param value The value to unbind.
   * @throws {TypeError} If the value is invalid for the property.
   */
  removeValue(value: T): void {
    if (!this.propertyType.isValueValid(value)) {
      throw new Error(`Invalid value for property "${this.propertyType.objectType.label}.${this.propertyType.label}"`);
    }
    const i = this.#value.indexOf(value);
    if (i !== -1) {
      this.#value.splice(i, 1);
    }
  }
}

/**
 * This class represents the int values bound to an {@link IntProperty} definition
 * with a `isUnique` field set to `false`.
 */
export class IntMultipleObjectPropertyValue extends MultipleObjectPropertyValue<number, IntProperty> {
  #unit: Unit | null;

  /**
   * Create a new int property value.
   * @param firstValue The first value to bind to the property.
   * @param propertyType The property to bind the value to.
   * @param unit Optional. The unit to attach to the values.
   * @throws {TypeError} If the value is invalid for the property
   *  or the unit’s type differs from the one defined by the property.
   */
  constructor(firstValue: number, propertyType: IntProperty, unit?: Unit) {
    super(firstValue, propertyType);
    this.unit = unit;
  }

  /**
   * The unit attached to the values. May be null.
   */
  get unit(): Unit | null {
    return this.#unit;
  }

  /**
   * Set the unit attached to the values. May be null.
   * @throws {TypeError} If the unit’s type differs from the one defined by the property.
   * @throws {Error} If the unit is null or undefined.
   */
  set unit(unit: Unit) {
    const expectedType = this.propertyType.unitType;
    if (!unit && !expectedType) {
      return;
    }
    if (!unit && expectedType) {
      throw new Error(`Undefined unit`);
    }
    if (unit && !expectedType) {
      throw new TypeError(`Unexpected unit for property "${this.propertyType.fullName}"`);
    }
    const actualType = unit.type;
    if (expectedType !== actualType) {
      throw new TypeError(`Invalid unit type for property "${this.propertyType.fullName}": expected "${expectedType?.label}", got "${actualType}"`);
    }
    this.#unit = unit;
  }
}

/**
 * This class represents the float values bound to an {@link FloatProperty} definition
 * with a `isUnique` field set to `false`.
 */
export class FloatMultipleObjectPropertyValue extends MultipleObjectPropertyValue<number, FloatProperty> {
  #unit: Unit | null;

  /**
   * Create a new float property value.
   * @param firstValue The first value to bind to the property.
   * @param propertyType The property to bind the value to.
   * @param unit Optional. The unit to attach to the values.
   * @throws {TypeError} If the value is invalid for the property
   *  or the unit’s type differs from the one defined by the property.
   */
  constructor(firstValue: number, propertyType: FloatProperty, unit?: Unit) {
    super(firstValue, propertyType);
    this.unit = unit;
  }

  /**
   * The unit attached to the values. May be null.
   */
  get unit(): Unit | null {
    return this.#unit;
  }

  /**
   * Set the unit attached to the values. May be null.
   * @throws {TypeError} If the unit’s type differs from the one defined by the property.
   * @throws {Error} If the unit is null or undefined.
   */
  set unit(unit: Unit) {
    const expectedType = this.propertyType.unitType;
    if (!unit && !expectedType) {
      return;
    }
    if (!unit && expectedType) {
      throw new Error(`Undefined unit`);
    }
    if (unit && !expectedType) {
      throw new TypeError(`Unexpected unit for property "${this.propertyType.fullName}"`);
    }
    const actualType = unit.type;
    if (expectedType !== actualType) {
      throw new TypeError(`Invalid unit type for property "${this.propertyType.fullName}": expected "${expectedType?.label}", got "${actualType}"`);
    }
    this.#unit = unit;
  }
}

/**
 * This class represents the string values bound to an {@link StringProperty} definition
 * with a `isUnique` field set to `false`.
 */
export class StringMultipleObjectPropertyValue extends MultipleObjectPropertyValue<string, StringProperty> {
  readonly #translations: { [langCode: string]: string }[] = [];

  /**
   * Create a new string property value.
   * @param firstValue The first value to bind to the property.
   * @param propertyType The property to bind the value to.
   * @param translations Optional. The existing translations for the value.
   * @throws {Error} If translations are provided but the property is not translatable.
   */
  constructor(firstValue: string, propertyType: StringProperty, translations?: { [langCode: string]: string }) {
    super(firstValue, propertyType);
    this.#ensureTranslatable();
    this.#translations.push({...translations});
  }

  /**
   * The translations for the string values.
   * @returns An ordered stream that contains streams of string pairs,
   *  each containing the language code and the text for that language in that order,
   *  for each value of this property.
   */
  get translations(): stream.Stream<stream.Stream<[string, string]>> {
    return stream.stream(this.#translations).map(t => stream.streamOfObject(t));
  }

  /**
   * Set the translation for the given language code and value index.
   * @param langCode The language code.
   * @param tr The translation for that language.
   * @param index The index of the value whose translation is to be modified.
   * @throws {Error} If the property is not translatable.
   */
  setTranslation(langCode: string, tr: string, index: number): void {
    this.#ensureTranslatable();
    this.#translations[index][langCode] = tr;
  }

  /**
   * Remove the translation for the given language code and value index.
   * @param langCode The language code.
   * @param index The index of the value whose translation is to be removed.
   * @throws {Error} If the property is not translatable.
   */
  removeTranslation(langCode: string, index: number): void {
    this.#ensureTranslatable();
    delete this.#translations[index][langCode];
  }

  #ensureTranslatable() {
    if (!this.propertyType.translatable) {
      throw new Error(`Property "${this.propertyType.fullName}" is not translatable`);
    }
  }
}
