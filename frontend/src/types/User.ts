interface UserArgs {
  userId: number;
  username: string;
}

export class User {
  userId: number;
  username: string;

  constructor({
                userId,
                username,
              }: UserArgs) {
    this.userId = userId;
    this.username = username;
  }
}


export default User;
