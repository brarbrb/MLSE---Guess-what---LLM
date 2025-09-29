interface UnlockableArgs {
  unlockableId: number;
  name: string;
  description: string;
}

export class Unlockable {
  unlockableId: number;
  name: string;
  description: string;

  constructor({
                unlockableId,
                name,
                description,
              }: UnlockableArgs) {
    this.unlockableId = unlockableId;
    this.name = name;
    this.description = description;
  }
}

export default Unlockable;
