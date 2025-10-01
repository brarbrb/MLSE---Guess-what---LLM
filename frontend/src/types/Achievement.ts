interface AchievementArgs {
  achievementId: number;
  name: string;
  description: string;
  iconUrl: string;
}

export class Achievement {
  achievementId: number;
  name: string;
  description: string;
  iconUrl: string;

  constructor({
                achievementId,
                name,
                description,
                iconUrl,
              }: AchievementArgs) {
    this.achievementId = achievementId;
    this.name = name;
    this.description = description;
    this.iconUrl = iconUrl;
  }
}

export default Achievement;
