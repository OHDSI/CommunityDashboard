import { Injectable } from '@angular/core';
import { CollectionPaths, IndexedDbDocs, TableData } from '@commonshcs-angular';
import { BehaviorSubject } from 'rxjs'

const demo = {
  'project': {
    'Common Data Model': {
      id: 'Common Data Model',
      featured: true,
      active: true,
    },
    'Hades': {
      id: 'Hades',
      featured: true,
      active: true,
    },
    'Atlas': {
      id: 'Atlas',
      featured: true,
      active: true,
    },
    'Perseus': {
      id: 'Perseus',
      featured: true,
      active: true,
    },
  }
}

const fixture = demo

@Injectable({
  providedIn: 'root'
})
export class DocsMock extends IndexedDbDocs {

  constructor(
  ) {
    const tables = new BehaviorSubject(fixture as CollectionPaths)
    super({tables})
  }

}