import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ActivatedRoute } from '@angular/router';
import { AfterViewInit } from '@angular/core';
import { DocsService } from '@commonshcs-angular';
import { BehaviorSubject, Subscription, concatMap, map, switchMap } from 'rxjs';
import { OnDestroy } from '@angular/core';
import { NetworkStudyRepo } from '../../network-study-repo.service';
import { StudyLeadComponent } from "../study-lead/study-lead.component"; 
import {MatChipsModule, MatChipInputEvent} from '@angular/material/chips';
import {MatIconModule} from '@angular/material/icon';
import { ReactiveFormsModule } from '@angular/forms';
import { FormControl } from '@angular/forms';
import {MatAutocompleteSelectedEvent, MatAutocompleteModule} from '@angular/material/autocomplete';
import {COMMA, ENTER} from '@angular/cdk/keycodes';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatButtonModule} from '@angular/material/button';
import { NetworkStudyChecklistComponent } from "../network-study-checklist/network-study-checklist.component";

@Component({
    selector: 'lib-repo-drilldown',
    standalone: true,
    templateUrl: './repo-drilldown.component.html',
    styleUrls: ['./repo-drilldown.component.css'],
    imports: [
        MatAutocompleteModule,
        MatIconModule,
        MatButtonModule,
        MatChipsModule,
        MatFormFieldModule,
        ReactiveFormsModule,
        CommonModule,
        StudyLeadComponent,
        NetworkStudyChecklistComponent
    ]
})
export class RepoDrilldownComponent implements AfterViewInit, OnDestroy {

  repo = new BehaviorSubject<NetworkStudyRepo|null>(null)
  crumb = this.repo.pipe(
    map(r => r?.name)
  )
  studyTypeControl = new FormControl('')
  separatorKeysCodes: number[] = [ENTER, COMMA]
  possibleTypesFiltered = this.studyTypeControl.valueChanges.pipe(
    map(v => ['hello', 'type'])
  )

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    @Inject('DocsService') private docsService: DocsService
  ){}
  
  ngAfterViewInit(): void {
    setTimeout(() => {
      this.subscriptions.push(this.route.paramMap.pipe(
        switchMap(ps => {
          const id = ps.get('repoId')
          return this.docsService.valueChanges<NetworkStudyRepo>({
            path: 'networkStudyRepo',
            where: [['id', '==', id]]
          })
        }),
        map(rs => rs[0])
      ).subscribe(this.repo))
    })
  }
    
  subscriptions: Subscription[] = []

  ngOnDestroy(): void {
    this.subscriptions.forEach(s => s.unsubscribe())
  }

  backToNetworkStudyList() {
    this.router.navigate(['network-studies'])
  }

  removeStudyType(t: string) {}

  addStudyType(event: MatChipInputEvent) {}

  selectedStudyType(event: MatAutocompleteSelectedEvent) {}
}
