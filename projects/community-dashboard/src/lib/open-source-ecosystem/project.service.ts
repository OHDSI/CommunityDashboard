import { Injectable } from '@angular/core';
import { TableFieldValue } from '@commonshcs-angular';

export interface Project {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  id: string,
  featured: true,
}

@Injectable({
  providedIn: 'root'
})
export class ProjectService {

  constructor() { }
}
