import { Component } from '@angular/core';
import { DocsService, Query, SearchService, SearchTableDataSource } from '@commonshcs-angular';
import { AfterViewInit } from '@angular/core';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTable, MatTableModule } from '@angular/material/table';
import { Inject } from '@angular/core';
import { OnDestroy } from '@angular/core';
import { switchMap } from 'rxjs/operators';
import { Router } from '@angular/router';
import { ActivatedRoute } from '@angular/router';
import { RouterModule } from '@angular/router';
import { ViewChild } from '@angular/core';
import { MatGridListModule } from '@angular/material/grid-list'; 
import { MatIconModule } from '@angular/material/icon'; 
import { MatButtonModule } from '@angular/material/button'; 
import { MatInputModule } from '@angular/material/input'; 
import { BehaviorSubject, Observable, Subscription, map, of, startWith } from 'rxjs';
import { CommonModule } from '@angular/common';
import { NetworkStudyCardComponent } from "../network-study-card/network-study-card.component";
import { FormControl } from '@angular/forms';
import { ReactiveFormsModule } from '@angular/forms';
import { NetworkStudyRepo } from '../../network-study-repo.service';
import { StudyLeadComponent } from "../study-lead/study-lead.component";

@Component({
    selector: 'lib-network-study-list',
    standalone: true,
    templateUrl: './network-study-list.component.html',
    styleUrls: ['./network-study-list.component.css'],
    imports: [
        MatTableModule,
        MatSortModule,
        MatPaginatorModule,
        MatGridListModule,
        MatButtonModule,
        MatIconModule,
        MatInputModule,
        RouterModule,
        ReactiveFormsModule,
        CommonModule,
        NetworkStudyCardComponent,
        StudyLeadComponent
    ]
})
export class NetworkStudyListComponent implements AfterViewInit, OnDestroy {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<NetworkStudyRepo>;

  searchControl = new FormControl('')
  mostWatchedStudies = this.docsService.valueChanges<NetworkStudyRepo>({
    path: 'networkStudyRepo',
    limit: 4,
  })
  lookingForDataPartners = this.docsService.valueChanges<NetworkStudyRepo>({
    path: 'networkStudyRepo',
    limit: 4,
  })
  displayedColumns = ['id', 'daysAtStage', 'protocol', 'results']
  dataSource!: SearchTableDataSource<NetworkStudyRepo>
  count = new BehaviorSubject(0)

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    @Inject('SearchService') private searchService: SearchService,
    @Inject('DocsService') private docsService: DocsService,
  ){}
  
  drillDown(study: NetworkStudyRepo) {
    this.router.navigate(['repo', study.id], {relativeTo: this.route})
  }
  
  ngAfterViewInit(): void {
    const searchQuery = this.searchControl.valueChanges.pipe(
      startWith(''),
      map((q) => {
        return {
          q: {
            value: q,
          }
        } as Query
      })
    )
    setTimeout(() => this.subscriptions.push(
      searchQuery.pipe(
        switchMap(query => this.searchService.count({
          index: 'networkStudyRepo',
          query
        }))
      ).subscribe(this.count)
    ))
    this.dataSource = new SearchTableDataSource(
      this.searchService,
      'networkStudyRepo',
      searchQuery
    )
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }

  subscriptions: Subscription[] = []

  ngOnDestroy(): void {
    for (const s of this.subscriptions) {
      s.unsubscribe()
    }
  }

}
