import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PhenotypeExplorerComponent } from './phenotype-explorer.component';

describe('PhenotypeExplorerComponent', () => {
  let component: PhenotypeExplorerComponent;
  let fixture: ComponentFixture<PhenotypeExplorerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ PhenotypeExplorerComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PhenotypeExplorerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
