import { Injectable } from "@angular/core"
import { AuthService, User } from "@community-dashboard/rest"
import { BehaviorSubject } from "rxjs"

export const TEST_USER: User = {
  uid: "46vdkIEuX7R3YhpiL92e",
  displayName: 'Test User',
  email: 'test@teststudysitemanager.onmicrosoft.com',
  photoURL: '',
} as any as User

@Injectable({
  providedIn: 'root'
})
export class AuthMockService implements AuthService {

  user = new BehaviorSubject<User | null>(TEST_USER)

  constructor(
  ) {}

}