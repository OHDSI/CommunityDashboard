import { InjectionToken } from '@angular/core';
import { Observable, Subject } from 'rxjs';

export interface Change {}

export type Id = number | string

export const RestToken = new InjectionToken<Rest>('RestToken')

export type FilterColumn = { 
  [key: string]: string | number | {
    like: string
  },
}

export type Where = { 
  [key: string]: string | number | FilterColumn[] | undefined | {
    like: string
  },
  or?: FilterColumn[]
}

export type Filter = {
  skip?: number,
  limit?: number,
  order?: string[],
  where?: Where,
}

export interface Rest {

  changes: Subject<Change>
  status: Observable<Error | null>

  create: {
    <T extends object>(params: {
      host: string,
      path: string,
      body: Omit<T, 'id'>
    })
    : Observable<T>;
  }

  replaceById: {
    <T extends {[key: string]: any}>(params: {
      host: string,
      path: string,
      id: Id,
      body: Omit<T, 'id'> | T
    }): Observable<T>
   }

  updateById: {
    <T extends {[key: string]: any}>(params: {
      host: string,
      path: string,
      id: Id,
      body: Partial<Omit<T, 'id'>> | T
    }): Observable<T>
  }

  find: {
    <T extends {[key: string]: any}>(params: {
      host: string,
      path: string,
      scope?: string,
      converter?: any,
      filter?: Filter,
    }): Observable<T[]>
  }

  findById: {
    <T>(params: {
      host: string,
      path: string,
      id: Id,
      scope?: string,
    }): Observable<T>
  }

  count: {
      (params: {
      host: string,
      path: string,
      filter?: {
        where?: { [key: string]: any },
      }
    }): Observable<number>
  }

}
