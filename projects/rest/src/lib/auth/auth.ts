import { BehaviorSubject } from "rxjs"

export interface User {
  uid: string,
  displayName: string,
  email: string,
  photoURL: string,
}

export interface AuthService {

  user: BehaviorSubject<User | null>

}