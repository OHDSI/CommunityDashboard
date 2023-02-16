import { AfterViewInit, Component, Input, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Funding, FundingService } from '../funding.service';
import { map, startWith } from 'rxjs';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTable, MatTableModule } from '@angular/material/table';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { Id, TableDataSource } from '@community-dashboard/rest';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { animate, state, style, transition, trigger } from '@angular/animations';

@Component({
  selector: 'lib-funding-table',
  standalone: true,
  imports: [
    MatInputModule,
    MatFormFieldModule,
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    FormsModule,
    ReactiveFormsModule,
    CommonModule
  ],
  templateUrl: './funding-table.component.html',
  styleUrls: ['./funding-table.component.css'],
  animations: [
    trigger('detailExpand', [
      state('collapsed', style({height: '0px', minHeight: '0'})),
      state('expanded', style({height: '*'})),
      transition('expanded <=> collapsed', animate('225ms cubic-bezier(0.4, 0.0, 0.2, 1)')),
    ]),
  ],
})
export class FundingTableComponent implements AfterViewInit, OnDestroy {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<Funding>;

  @Input() stage!: string

  searchControl = new FormControl('')
  filter = this.searchControl.valueChanges.pipe(
    map(v => {
      if (v === '') {
        return {}
      }
      return {
        where: {
          or: [
            {'LOCATION FOUND': {like: v}},
            {'LOCATION FOUND 2': {like: v}},
            {'AGENCY': {like: v}},
            {'OPPORTUNITY DETAILS': {like: v}},
          ]
        }
      }
    })
  )
  dataSource!: TableDataSource<Funding>
  count!: number

  @Input()
  displayedColumns: string[] = [
    // "DATE ADDED",
    // "LOCATION FOUND",
    // "LOCATION FOUND 2",
    "AGENCY",
    "OPPORTUNITY DETAILS",
    // "OPPORTUNITY LINK",
    // "BUDGET",
    // "NUMBER YEARS",
    "SUBMISSION DEADLINE(S) IN 2023",
  ]
  columnsToDisplayWithExpand = ['expand', ...this.displayedColumns]
  expanded: {id: Id} | null = null

  records = this.fundingService.find().pipe(
    map(r => JSON.stringify(r))
  )

  constructor(
    private fundingService: FundingService,
  ) {}

  ngAfterViewInit(): void {
    this.dataSource = new TableDataSource(
      this.fundingService, undefined, 
      this.filter
    )
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }

  filterSub = this.filter.pipe(startWith({})).subscribe(f => {
    this.fundingService.count({filter: f}).subscribe(c => this.count = c)
  })

  ngOnDestroy(): void {
    this.filterSub.unsubscribe()
  }

  // search(d: StudyPromotion) {
  //   const search = this.studyProgressSearchControl.value
  //   if (!search) { return false }
  //   return d.tags.join(' ').toLowerCase().includes(search.toLowerCase()) ||
  //     d.repoName.toLowerCase().includes(search.toLowerCase()) ||
  //     d.useCases.join(' ').toLowerCase().includes(search.toLowerCase()) ||
  //     d.studyType.join(' ').toLowerCase().includes(search.toLowerCase())
  // }

  toggleRow(row: Funding) {
    if (this.expanded?.id === row.id) {
      this.expanded = null
    } else {
      this.expanded = {id: row.id}
    }
  }
}
