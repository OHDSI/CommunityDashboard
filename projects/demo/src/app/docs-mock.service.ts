import { Injectable } from '@angular/core';
import { CollectionPaths, IndexedDbDocs } from '@commonshcs-angular';
import { BehaviorSubject } from 'rxjs'
import * as project from '../../test/demo/project.json'
import * as networkStudyRepo from '../../test/demo/networkStudyRepo.json'

const demo = {
  'project': project,
  'networkStudyRepo': networkStudyRepo,
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