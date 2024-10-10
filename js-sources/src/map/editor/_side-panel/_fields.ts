import $ from "jquery";

import {
  BoolPropertyValue,
  EnumPropertyValue,
  FloatPropertyValue,
  IntPropertyValue,
  NumberProperty,
  NumberPropertyValue,
  ObjectProperty,
  PropertyValue,
  StringPropertyValue,
  Unit,
} from "../../model/types";
import Component from "./_component";

export abstract class ValueField<
  T,
  OP extends PropertyValue<T, ObjectProperty<T>>,
> extends Component {
  readonly property: OP;
  readonly #$container: JQuery<HTMLDivElement>;

  protected constructor(property: OP) {
    super();
    this.property = property;
    this.#$container = $(`<div class="form-group row">
  <label class="col-sm-1 col-form-label" for="${property.propertyType.fullName}">
    ${property.propertyType.localizedName}
  </label>
</div>`);
    this.#$container.append(
      $('<div class="col-sm-2"></div>').append(this.getInputField()),
    );
  }

  protected abstract getInputField(): JQuery;

  get container(): JQuery {
    return this.#$container;
  }

  get visible(): boolean {
    return this.#$container.is(":visible");
  }

  set visible(visible: boolean) {
    if (visible) {
      this.#$container.show();
    } else {
      this.#$container.hide();
    }
  }
}

export abstract class SingleValueField<
  T,
  OP extends PropertyValue<T, ObjectProperty<T>>,
> extends ValueField<T, OP> {
  #isNull = true;

  protected constructor(property: OP) {
    super(property);
    if (!property.propertyType.isUnique)
      throw new Error(
        `Property ${property.propertyType.fullName} is not unique`,
      );
  }

  get isNull(): boolean {
    return this.#isNull;
  }

  getValue(): T | null {
    return this.property.value;
  }

  setValue(value: T | null): void {
    this.updateValue(value);
    this.setFieldValue(value);
  }

  protected updateValue(value: T | null) {
    this.#isNull = value === null;
    if (!this.#isNull && !this.property.propertyType.isValueValid(value as T)) {
      this.property.value = value as T;
    }
  }

  protected abstract setFieldValue(value: T | null): void;
}

export class BooleanSingleValueField extends SingleValueField<
  boolean,
  BoolPropertyValue
> {
  readonly #$input: JQuery<HTMLInputElement>;

  constructor(property: BoolPropertyValue) {
    super(property);
    this.#$input = $('<input type="checkbox" class="form-check-input">');
    this.#$input.on("click", () => {
      if (this.#$input.prop("indeterminate")) this.setValue(false);
      else if (this.#$input.prop("checked")) this.setValue(null);
      else this.setValue(true);
    });
  }

  protected getInputField(): JQuery {
    return this.#$input;
  }

  protected setFieldValue(value: boolean | null): void {
    if (value === null) {
      this.#$input.prop("indeterminate", true);
    } else {
      this.#$input.prop("indeterminate", false); // TODO check if necessary
      this.#$input.prop("checked", value);
    }
  }
}

export abstract class NumberSingleValueField<
  OP extends NumberPropertyValue<NumberProperty>,
> extends SingleValueField<number, OP> {
  protected readonly $input: JQuery<HTMLInputElement>;
  readonly #$unitSelector: JQuery<HTMLSelectElement> | null;
  readonly #$div: JQuery<HTMLDivElement>;
  #internalInputUpdate = false;
  #internalUnitUpdate = false;

  protected constructor(property: OP) {
    super(property);
    this.$input = $(
      `<input type="number" id="${this.property.propertyType.fullName}" class="form-control">`,
    );
    if (property.propertyType.min !== null) {
      this.$input.attr("min", property.propertyType.min);
    }
    if (property.propertyType.max !== null) {
      this.$input.attr("max", property.propertyType.max);
    }
    this.$input.on("change", () => {
      if (this.#internalInputUpdate) {
        return;
      }
      const value = this.$input.val();
      this.updateValue(value ? +value : null);
    });

    if (property.propertyType.unitType) {
      this.#$unitSelector = $('<select class="custom-select"></select>');
      const units = new Map<string, Unit>();
      property.propertyType.unitType.units.forEach((unit) => {
        units.set(unit.symbol, unit);
      });
      for (const symbol of units.keys())
        this.#$unitSelector.append(
          $(`<option value="${symbol}">${symbol}</option>`),
        );
      this.#$unitSelector.on("change", () => {
        if (!this.#internalUnitUpdate && this.#$unitSelector) {
          const unit = units.get(this.#$unitSelector.val() as string);
          if (unit) this.#updateUnit(unit);
        }
      });
      this.#$div = $(`<div class="input-group">
  <div class="input-group-append"></div>
</div>`);
      this.#$div.find("div").append(this.#$unitSelector);
      this.#$div.prepend(this.$input);
    } else {
      this.#$unitSelector = null;
      this.#$div = this.$input;
    }
  }

  getUnit(): Unit | null {
    return this.property.unit;
  }

  setUnit(unit: Unit): void {
    this.#updateUnit(unit);
    this.#setUnitSelector(unit);
  }

  #updateUnit(unit: Unit): void {
    this.property.unit = unit;
  }

  #setUnitSelector(unit: Unit): void {
    if (this.#$unitSelector) {
      this.#internalUnitUpdate = true;
      this.#$unitSelector.val(unit.symbol);
      this.#internalUnitUpdate = false;
    }
  }

  protected getInputField(): JQuery {
    return this.#$div;
  }

  protected setFieldValue(value: number | null): void {
    this.#internalInputUpdate = true;
    this.$input.val(value?.toString() ?? "");
    this.#internalInputUpdate = false;
  }
}

export class IntSingleValueField extends NumberSingleValueField<IntPropertyValue> {
  constructor(property: IntPropertyValue) {
    super(property);
    this.$input.attr("step", 1);
  }
}

export class FloatSingleValueField extends NumberSingleValueField<FloatPropertyValue> {
  constructor(property: FloatPropertyValue) {
    super(property);
    this.$input.attr("step", "any");
  }
}

export class StringSingleValueField extends SingleValueField<
  string,
  StringPropertyValue
> {
  readonly #$input: JQuery<HTMLInputElement | HTMLTextAreaElement>;
  #internalInputUpdate = false;

  constructor(property: StringPropertyValue) {
    super(property);
    if (property.propertyType.multiline)
      this.#$input = $('<textarea class="form-control" rows="4"></textarea>');
    else this.#$input = $('<input type="text" class="form-control">');
    this.#$input.on("change", () => {
      if (!this.#internalInputUpdate)
        this.updateValue(this.#$input.val() ?? null);
    });
  }

  protected getInputField(): JQuery {
    return this.#$input;
  }

  protected setFieldValue(value: string | null): void {
    this.#internalInputUpdate = true;
    this.#$input.val(value ?? "");
    this.#internalInputUpdate = false;
  }

  // TODO handle translations
}

// TODO date interval field
// TODO type field
// TODO temporal field

export abstract class EnumSingleValueField extends SingleValueField<
  string,
  EnumPropertyValue
> {
  readonly #$input: JQuery<HTMLSelectElement>;
  #internalInputUpdate = false;

  protected constructor(property: EnumPropertyValue) {
    super(property);
    this.#$input = $('<select class="custom-select"></select>');
    const enumValues = new Map<string, string>();
    property.propertyType.enumType.valuesTranslations[0]?.forEach(
      ([langCode, text]) => {
        enumValues.set(langCode, text);
      },
    );
    const defaultText = "— Choose —"; // TODO translate
    this.#$input.append($(`<option value="">${defaultText}</option>`));
    for (const [label, tr] of Object.entries(enumValues))
      this.#$input.append($(`<option value="${label}">${tr}</option>`));
    this.#$input.on("change", () => {
      if (!this.#internalInputUpdate) {
        const value = this.#$input.val() as string | undefined;
        this.updateValue(
          typeof value === "string" ? (enumValues.get(value) ?? null) : null,
        );
      }
    });
  }

  protected getInputField(): JQuery {
    return this.#$input;
  }

  protected setFieldValue(value: string | null): void {
    this.#internalInputUpdate = true;
    this.#$input.val(value ?? "");
    this.#internalInputUpdate = false;
  }
}
