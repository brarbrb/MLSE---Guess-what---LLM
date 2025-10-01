/**
 * Convert a string to a lower camelCase format.
 * For example, "This is_reallyCool" -> "thisIsReallyCool".
 */
function toLowerCamelCase(name: string): string {
  return name.replace(/(?:^|[_\s]+)(.?)/gi, (_match, firstChar, i) => (
    i ? firstChar.toUpperCase() : firstChar.toLowerCase()
  ));
}


/**
 * Convert a string to a upper camelCase format.
 * For example, "This is_reallyCool" -> "ThisIsReallyCool".
 */
function toUpperCamelCase(name: string): string {
  return name.replace(/(?:^|[_\s]+)(.?)/gi, (_match, firstChar) => (
    firstChar.toUpperCase()
  ));
}


/**
 * Create a new instance of a class from a JSON object we get from the backend api.
 * @param klass - a class type object to create an instance of.
 * @param data - JSON data without objects and lists.
 */
function fromJSON<T extends object, TArgs extends { [key: string]: any }>(
  klass: { name: string, new(args: TArgs): T },
  data: { [key: string]: any }): T {
  const args: { [key: string]: any } = {};
  Object.entries(data).map(([key, value]) => {
    const arg = toLowerCamelCase(key);
    if (arg in args) {
      console.error(`${arg} was defined more than once in ${klass.name}`, data);
    }
    if (typeof value === "object") {
      console.error(`${key} is an object and cannot be used to initialize ${klass.name}`, data);
    } else if (value !== null && value !== undefined) {
      args[arg] = value;
    }
  });
  const instance = new klass(args as TArgs);
  const undefinedParams = Object.entries(instance)
    .filter(([, value]) => (value === undefined))
    .map(([key]) => key);
  if (undefinedParams.length) {
    console.error(`initialized ${klass.name} with missing arguments: `, undefinedParams, data);
  }
  return instance;
}
