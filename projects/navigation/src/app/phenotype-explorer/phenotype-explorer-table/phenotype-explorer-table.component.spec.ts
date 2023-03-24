import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PhenotypeExplorerTableComponentComponent } from './phenotype-explorer-table.component';

describe('PhenotypeExplorerTableComponentComponent', () => {
  let component: PhenotypeExplorerTableComponentComponent;
  let fixture: ComponentFixture<PhenotypeExplorerTableComponentComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ PhenotypeExplorerTableComponentComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PhenotypeExplorerTableComponentComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
