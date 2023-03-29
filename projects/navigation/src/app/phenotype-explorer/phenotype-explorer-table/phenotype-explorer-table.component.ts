import { AfterViewInit, Component, ElementRef, Input, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTable, MatTableModule } from '@angular/material/table';
import { Phenotype, PhenotypeService } from '../phenotype.service';
import { TableDataSource } from '@community-dashboard/rest';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import {MatAutocompleteModule, MatAutocompleteSelectedEvent} from '@angular/material/autocomplete';
import { MatInputModule } from '@angular/material/input';
import {MatChipInputEvent, MatChipsModule} from '@angular/material/chips';
import {COMMA, ENTER} from '@angular/cdk/keycodes';
import { concatMap, map, Observable, of, startWith, tap } from 'rxjs';
import { MatIconModule } from '@angular/material/icon';


@Component({
  selector: 'app-phenotype-explorer-table-component',
  standalone: true,
  imports: [
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    MatFormFieldModule,
    MatAutocompleteModule,
    MatInputModule,
    MatChipsModule,
    MatIconModule,
    ReactiveFormsModule,
    FormsModule,
    CommonModule
  ],
  templateUrl: './phenotype-explorer-table.component.html',
  styleUrls: ['./phenotype-explorer-table.component.css']
})
export class PhenotypeExplorerTableComponentComponent implements AfterViewInit, OnDestroy{
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<Phenotype>;
  @ViewChild('hashTagInput') hashTagInput!: ElementRef<HTMLInputElement>;

  searchControl = new FormControl('')
  hashTagControl = new FormControl('');
  statusControl = new FormControl('');

  dataSource!: TableDataSource<Phenotype>
  count = this.phenotypeService.count()
  separatorKeysCodes: number[] = [ENTER, COMMA];
  filteredHashTags: Observable<string[]> = this.hashTagControl.valueChanges.pipe(
    startWith(null),
    concatMap((h: string | null) => (h ? this._filter(h) : of(null))),
    concatMap(hs => hs ? of(hs) : this.allHashTags)
  )
  hashTags: string[] = [];
  allHashTags: Observable<string[]> = this.phenotypeService.hashtags.pipe(
    map(hs => [...hs])
  );
  status = this.phenotypeService.status

  @Input()
  displayedColumns: string[] = [
    'cohortId', 'cohortName', 'status','Forum', 'modifiedDate','hashTag', 'publications', 'networkStudies'
  ]

  constructor(
    private phenotypeService: PhenotypeService,
  ) {}

  ngAfterViewInit(): void {
    this.dataSource = new TableDataSource(
      this.phenotypeService
    )
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }

  statusControlSubscription = this.statusControl.valueChanges.subscribe(
    s => this.phenotypeService.filterStatus.next(s)
  )
  searchSub = this.searchControl.valueChanges.subscribe(
    (v => {
      this.phenotypeService.search.next(v ?? '')
    })
  )

  ngOnDestroy(): void {
    this.statusControlSubscription.unsubscribe()
    this.searchSub.unsubscribe()
  }

  threadNumber(href: string) {
    const path = href.split('/')
    return path[path.length - 1]
  }

  add(event: MatChipInputEvent): void {
    const value = (event.value || '').trim();
    if (value) {
      this.hashTags.push(value);
      this.phenotypeService.filterHash.next(this.hashTags.length ? this.hashTags : null)
    }
    event.chipInput!.clear();
    this.hashTagControl.setValue(null);
  }

  remove(h: string): void {
    const index = this.hashTags.indexOf(h);

    if (index >= 0) {
      this.hashTags.splice(index, 1);
    }

    this.phenotypeService.filterHash.next(this.hashTags.length ? this.hashTags : null)
  }

  selected(event: MatAutocompleteSelectedEvent): void {
    this.hashTags.push(event.option.viewValue);
    this.phenotypeService.filterHash.next(this.hashTags.length ? this.hashTags : null)
    this.hashTagInput.nativeElement.value = '';
    this.hashTagControl.setValue(null);
  }

  private _filter(value: string): Observable<string[]> {
    const filterValue = value.toLowerCase();
    return this.allHashTags.pipe(
      map(hs => hs.filter(h => h.toLowerCase().includes(filterValue)))
    );
  }
}